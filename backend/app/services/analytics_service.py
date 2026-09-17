"""Analytics & demand intelligence (blueprint §33, §34, §102, §156).

Every number on a dashboard is computed from real event/order rows. Where no
data exists the API returns zeros / "no data" — never fabricated metrics.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.models.analytics import AnalyticsEvent, DemandSignal
from app.models.commerce import Order, OrderItem, OrderStatus
from app.models.engagement import Review
from app.models.product import Product
from app.models.profile import ArtisanProfile, Cluster, ClusterMember
from app.models.user import User

PAID_STATUSES = ("CONFIRMED", "PROCESSING", "IN_PRODUCTION", "READY_TO_SHIP", "SHIPPED", "DELIVERED", "COMPLETED")


class AnalyticsService:
    # ---------------------------------------------------------------- track

    def track(self, db: Session, *, event_type: str, actor: Optional[User],
              entity_type: Optional[str] = None, entity_id: Optional[str] = None,
              payload: Optional[dict] = None) -> None:
        db.add(AnalyticsEvent(
            event_type=event_type,
            actor_id=actor.id if actor else None,
            actor_role=actor.role if actor else None,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        ))

    def increment_view(self, db: Session, product: Product, actor: Optional[User]) -> None:
        product.view_count += 1
        self.track(db, event_type="PRODUCT_VIEWED", actor=actor, entity_type="product", entity_id=product.id)

    # ------------------------------------------------------------- artisan

    def artisan_dashboard(self, db: Session, *, artisan_id: str) -> dict:
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        revenue = (
            db.query(func.coalesce(func.sum(OrderItem.line_total), 0.0))
            .join(Order, OrderItem.order_id == Order.id)
            .filter(OrderItem.artisan_id == artisan_id, Order.status.in_(PAID_STATUSES))
            .scalar()
        ) or 0.0

        orders_count = (
            db.query(func.count(distinct(OrderItem.order_id)))
            .filter(OrderItem.artisan_id == artisan_id)
            .scalar()
        ) or 0

        buyers = (
            db.query(func.count(distinct(Order.buyer_id)))
            .join(OrderItem, OrderItem.order_id == Order.id)
            .filter(OrderItem.artisan_id == artisan_id)
            .scalar()
        ) or 0

        repeat_buyers = (
            db.query(func.count(distinct(Order.buyer_id)))
            .join(OrderItem, OrderItem.order_id == Order.id)
            .filter(OrderItem.artisan_id == artisan_id)
            .group_by(Order.buyer_id)
            .having(func.count(distinct(OrderItem.order_id)) > 1)
            .count()
        ) or 0

        month_revenue = (
            db.query(func.coalesce(func.sum(OrderItem.line_total), 0.0))
            .join(Order, OrderItem.order_id == Order.id)
            .filter(OrderItem.artisan_id == artisan_id, Order.status.in_(PAID_STATUSES), Order.created_at >= month_start)
            .scalar()
        ) or 0.0

        aov = (float(revenue) / orders_count) if orders_count else 0.0

        top_products = (
            db.query(OrderItem.product_title_snapshot, func.sum(OrderItem.quantity).label("units"), func.sum(OrderItem.line_total).label("revenue"))
            .join(Order, OrderItem.order_id == Order.id)
            .filter(OrderItem.artisan_id == artisan_id, Order.status.in_(PAID_STATUSES))
            .group_by(OrderItem.product_title_snapshot)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(5)
            .all()
        )

        demand_rows = (
            db.query(Product)
            .filter(Product.artisan_id == artisan_id, Product.lifecycle == "PUBLISHED")
            .order_by(Product.view_count.desc())
            .limit(5)
            .all()
        )

        return {
            "today": self._artisan_today(db, artisan_id),
            "totals": {
                "revenue": float(revenue),
                "month_revenue": float(month_revenue),
                "orders": int(orders_count),
                "unique_buyers": int(buyers),
                "repeat_buyers": int(repeat_buyers),
                "repeat_rate": round(repeat_buyers / buyers * 100, 1) if buyers else 0.0,
                "avg_order_value": round(aov, 2),
            },
            "top_products": [
                {"title": t or "Untitled", "units": int(u or 0), "revenue": float(r or 0)} for t, u, r in top_products
            ],
            "most_viewed": [
                {"title": p.title or "Untitled", "views": p.view_count, "id": p.id} for p in demand_rows
            ],
        }

    def _artisan_today(self, db: Session, artisan_id: str) -> dict:
        from app.models.commerce import CustomRequest

        open_orders = (
            db.query(func.count(distinct(OrderItem.order_id)))
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .filter(OrderItem.artisan_id == artisan_id, Order.status.in_(["CONFIRMED", "PROCESSING", "IN_PRODUCTION"]))
            .scalar()
        ) or 0
        enquiries = (
            db.query(func.count(CustomRequest.id))
            .filter(CustomRequest.artisan_id == artisan_id, CustomRequest.status == "OPEN")
            .scalar()
        ) or 0
        return {
            "new_orders": int(open_orders),
            "enquiries": int(enquiries),
        }

    # --------------------------------------------------------------- admin

    def admin_overview(self, db: Session) -> dict:
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        gmv = (
            db.query(func.coalesce(func.sum(Order.total), 0.0))
            .filter(Order.status.in_(PAID_STATUSES))
            .scalar()
        ) or 0.0
        return {
            "artisans": int(db.query(func.count(ArtisanProfile.id)).scalar() or 0),
            "active_products": int(db.query(func.count(Product.id)).filter(Product.lifecycle == "PUBLISHED").scalar() or 0),
            "orders": int(db.query(func.count(Order.id)).filter(Order.status != OrderStatus.DRAFT).scalar() or 0),
            "gmv": float(gmv),
            "buyers": int(db.query(func.count(User.id)).filter(User.role.in_(["BUYER", "B2B_BUYER"])).scalar() or 0),
            "repeat_rate": self._platform_repeat_rate(db),
            "month_gmv": float(
                db.query(func.coalesce(func.sum(Order.total), 0.0))
                .filter(Order.status.in_(PAID_STATUSES), Order.created_at >= month_start)
                .scalar() or 0.0
            ),
        }

    def _platform_repeat_rate(self, db: Session) -> float:
        buyers = (
            db.query(func.count(distinct(Order.buyer_id))).filter(Order.status.in_(PAID_STATUSES)).scalar()
        ) or 0
        if not buyers:
            return 0.0
        repeat = (
            db.query(func.count(distinct(Order.buyer_id)))
            .filter(Order.status.in_(PAID_STATUSES))
            .group_by(Order.buyer_id)
            .having(func.count(Order.id) > 1)
            .count()
        ) or 0
        return round(repeat / buyers * 100, 1)

    # -------------------------------------------------------------- impact

    def impact(self, db: Session) -> dict:
        return {
            "artisans_onboarded": int(db.query(func.count(ArtisanProfile.id)).scalar() or 0),
            "products_catalogued": int(db.query(func.count(Product.id)).filter(Product.deleted_at.is_(None)).scalar() or 0),
            "orders_completed": int(db.query(func.count(Order.id)).filter(Order.status == OrderStatus.COMPLETED).scalar() or 0),
            "artisans_with_orders": int(
                db.query(func.count(distinct(OrderItem.artisan_id))).scalar() or 0
            ),
            "note": "All figures are computed from actual platform records.",
        }

    # ------------------------------------------------------------- clusters

    def cluster_analytics(self, db: Session, *, cluster_id: str) -> dict:
        member_rows = db.query(ClusterMember).filter(ClusterMember.cluster_id == cluster_id).all()
        artisan_ids = [m.artisan_id for m in member_rows]
        if not artisan_ids:
            return {"artisans": 0, "products": 0, "orders": 0, "revenue": 0.0, "top_crafts": []}
        products = int(db.query(func.count(Product.id)).filter(Product.artisan_id.in_(artisan_ids), Product.deleted_at.is_(None)).scalar() or 0)
        revenue = (
            db.query(func.coalesce(func.sum(OrderItem.line_total), 0.0))
            .join(Order, OrderItem.order_id == Order.id)
            .filter(OrderItem.artisan_id.in_(artisan_ids), Order.status.in_(PAID_STATUSES))
            .scalar()
        ) or 0.0
        orders = (
            db.query(func.count(distinct(OrderItem.order_id)))
            .filter(OrderItem.artisan_id.in_(artisan_ids))
            .scalar()
        ) or 0
        crafts = (
            db.query(ArtisanProfile.craft_specialization, func.count(ArtisanProfile.id))
            .filter(ArtisanProfile.id.in_(artisan_ids), ArtisanProfile.craft_specialization.isnot(None))
            .group_by(ArtisanProfile.craft_specialization)
            .order_by(func.count(ArtisanProfile.id).desc())
            .limit(5)
            .all()
        )
        return {
            "artisans": len(artisan_ids),
            "products": products,
            "orders": int(orders),
            "revenue": float(revenue),
            "top_crafts": [{"craft": c or "Unspecified", "artisans": int(n)} for c, n in crafts],
        }


analytics_service = AnalyticsService()
