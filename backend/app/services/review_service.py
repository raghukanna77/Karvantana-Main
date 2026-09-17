"""Reviews & reputation (blueprint §24, §38, §125).

Reviews are gated on completed orders — one per order item, verified purchase
only. Reputation aggregates (rating, repeat buyers, fulfilment) are recomputed
from actual transaction history; nothing is fabricated.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationFailedError
from app.core.events import bus, REVIEW_CREATED
from app.models.commerce import Order, OrderItem, OrderStatus
from app.models.engagement import ArtisanReputation, Review
from app.models.product import Product
from app.services.notification_service import notification_service

VALID_RATINGS = (1, 2, 3, 4, 5)
COMPLETED_STATUSES = (OrderStatus.COMPLETED, OrderStatus.DELIVERED)


class ReviewService:
    def create_review(
        self,
        db: Session,
        *,
        buyer: User,
        order_item_id: str,
        product_rating: int,
        text: Optional[str] = None,
        quality_rating: Optional[int] = None,
        communication_rating: Optional[int] = None,
        value_rating: Optional[int] = None,
        delivery_rating: Optional[int] = None,
    ) -> Review:
        if product_rating not in VALID_RATINGS:
            raise ValidationFailedError("Choose a rating between 1 and 5 stars.")
        for extra in (quality_rating, communication_rating, value_rating, delivery_rating):
            if extra is not None and extra not in VALID_RATINGS:
                raise ValidationFailedError("Ratings must be between 1 and 5 stars.")

        item = db.query(OrderItem).filter(OrderItem.id == order_item_id).first()
        if item is None:
            raise NotFoundError("Order item not found.")
        order = db.query(Order).filter(Order.id == item.order_id).first()
        if order is None or order.buyer_id != buyer.id:
            raise PermissionDeniedError("You can only review your own purchases.")
        if order.status not in COMPLETED_STATUSES:
            raise ValidationFailedError("You can review after the order is delivered or completed.")
        if db.query(Review).filter(Review.order_item_id == order_item_id).first():
            raise ConflictError("You already reviewed this purchase.")

        review = Review(
            product_id=item.product_id,
            artisan_id=item.artisan_id,
            buyer_id=buyer.id,
            order_item_id=order_item_id,
            product_rating=product_rating,
            quality_rating=quality_rating,
            communication_rating=communication_rating,
            value_rating=value_rating,
            delivery_rating=delivery_rating,
            text=(text or None),
            is_verified_purchase=True,
        )
        db.add(review)
        db.flush()
        self._recompute_artisan_reputation(db, item.artisan_id)
        bus.publish(REVIEW_CREATED, {"review_id": review.id, "artisan_id": item.artisan_id})
        notification_service.create(
            db, user_id=self._artisan_user(db, item.artisan_id), type="REVIEW_RECEIVED",
            title="New review from a buyer",
            body=f"A buyer rated your product {product_rating}★.",
            link="/artisan/insights",
        )
        return review

    def product_reviews(self, db: Session, product_id: str) -> list[Review]:
        return (
            db.query(Review)
            .filter(Review.product_id == product_id)
            .order_by(Review.created_at.desc())
            .all()
        )

    def _recompute_artisan_reputation(self, db: Session, artisan_id: str) -> None:
        rating_agg = db.query(func.avg(Review.product_rating), func.count(Review.id)).filter(
            Review.artisan_id == artisan_id
        ).one()
        avg, count = (float(rating_agg[0] or 0), int(rating_agg[1] or 0))

        completed_orders = (
            db.query(func.count(distinct(OrderItem.order_id)))
            .filter(OrderItem.artisan_id == artisan_id, Order.status.in_(COMPLETED_STATUSES))
            .join(Order, OrderItem.order_id == Order.id)
            .scalar() or 0
        )
        repeat_buyers = (
            db.query(func.count(distinct(Order.buyer_id)))
            .join(OrderItem, OrderItem.order_id == Order.id)
            .filter(OrderItem.artisan_id == artisan_id)
            .group_by(Order.buyer_id)
            .having(func.count(distinct(Order.id)) > 1)
            .count()
        )
        rep = db.query(ArtisanReputation).filter(ArtisanReputation.artisan_id == artisan_id).first()
        if rep is None:
            rep = ArtisanReputation(artisan_id=artisan_id)
            db.add(rep)
        rep.rating_avg = round(avg, 2)
        rep.rating_count = count
        rep.verified_orders = int(completed_orders)
        rep.repeat_buyers = int(repeat_buyers)

    def _artisan_user(self, db: Session, artisan_id: str) -> Optional[str]:
        from app.models.profile import ArtisanProfile

        profile = db.query(ArtisanProfile).filter(ArtisanProfile.id == artisan_id).first()
        return profile.user_id if profile else None


review_service = ReviewService()
