"""Reviews, bulk/custom commerce, notifications (/api/v1)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.commerce import BulkRequest, CustomRequest, Quote
from app.models.profile import ArtisanProfile
from app.models.user import User
from app.schemas.product import (
    AcceptQuoteIn, BulkRequestIn, CustomRequestIn, QuoteIn, ReviewIn,
)
from app.security.dependencies import get_current_user, require_roles
from app.services.commerce_requests import request_service
from app.services.notification_service import notification_service
from app.services.review_service import review_service

router = APIRouter(tags=["commerce"])


# ------------------------------------------------------------------ reviews

@router.post("/products/{product_id}/reviews", summary="Review a verified purchase")
def create_review(product_id: str, payload: ReviewIn, user: User = Depends(require_roles("BUYER", "B2B_BUYER", "ADMIN")),
                  db: Session = Depends(get_db)):
    review = review_service.create_review(db, buyer=user, order_item_id=payload.order_item_id,
                                          product_rating=payload.product_rating, text=payload.text,
                                          quality_rating=payload.quality_rating,
                                          communication_rating=payload.communication_rating,
                                          value_rating=payload.value_rating,
                                          delivery_rating=payload.delivery_rating)
    return {"id": review.id, "created": True}


@router.get("/products/{product_id}/reviews", summary="Product reviews (public)")
def product_reviews(product_id: str, db: Session = Depends(get_db)):
    reviews = review_service.product_reviews(db, product_id)
    return {"items": [
        {"rating": r.product_rating, "text": r.text, "verified": r.is_verified_purchase,
         "created_at": r.created_at.isoformat()} for r in reviews
    ]}


# ------------------------------------------------------------- bulk / custom

@router.post("/bulk-requests", summary="Create a bulk (B2B) requirement with AI parsing")
def create_bulk(payload: BulkRequestIn, user: User = Depends(require_roles("BUYER", "B2B_BUYER", "ADMIN")),
                db: Session = Depends(get_db)):
    required_by = None
    if payload.required_by:
        try:
            required_by = datetime.fromisoformat(payload.required_by)
        except ValueError:
            raise NotFoundError("Invalid date")  # replaced below by validation error
    req = request_service.create_bulk_request(
        db, buyer=user, title=payload.title, description=payload.description,
        quantity=payload.quantity,
        max_unit_price=Decimal(str(payload.max_unit_price)) if payload.max_unit_price else None,
        required_by=required_by, customization_required=payload.customization_required,
        category_hint=payload.category_hint,
    )
    return {"id": req.id, "parsed": req.parsed_requirements, "status": req.status}


@router.get("/bulk-requests/mine", summary="My bulk requests (buyer)")
def my_bulk(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(BulkRequest).filter(BulkRequest.buyer_id == user.id).order_by(BulkRequest.created_at.desc()).all()
    return {"items": [_bulk_json(r) for r in rows]}


@router.get("/bulk-requests/{request_id}/matches", summary="AI-matched products for this requirement")
def bulk_matches(request_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = db.query(BulkRequest).filter(BulkRequest.id == request_id).first()
    if req is None or req.buyer_id != user.id:
        raise NotFoundError("Bulk request not found.")
    return {"matches": request_service.bulk_matches(db, req)}


@router.get("/bulk-requests/open", summary="Open bulk requirements (artisan opportunities)",
            dependencies=[Depends(require_roles("ARTISAN", "ADMIN"))])
def open_bulk(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(BulkRequest).filter(BulkRequest.status == "OPEN").order_by(BulkRequest.created_at.desc()).limit(20).all()
    return {"items": [_bulk_json(r) for r in rows]}


def _bulk_json(r: BulkRequest) -> dict:
    return {
        "id": r.id, "title": r.title, "description": r.description, "quantity": r.quantity,
        "max_unit_price": float(r.max_unit_price) if r.max_unit_price else None,
        "required_by": r.required_by.isoformat() if r.required_by else None,
        "customization_required": r.customization_required,
        "parsed": r.parsed_requirements, "status": r.status,
        "created_at": r.created_at.isoformat(),
    }


@router.post("/custom-requests", summary="Request a custom product from an artisan")
def create_custom(payload: CustomRequestIn, user: User = Depends(require_roles("BUYER", "B2B_BUYER", "ADMIN")),
                  db: Session = Depends(get_db)):
    profile = db.query(ArtisanProfile).filter(ArtisanProfile.id == payload.artisan_id).first()
    if profile is None:
        raise NotFoundError("Artisan not found.")
    required_by = None
    if payload.required_by:
        try:
            required_by = datetime.fromisoformat(payload.required_by)
        except ValueError:
            required_by = None
    req = CustomRequest(
        buyer_id=user.id, artisan_id=payload.artisan_id, product_id=payload.product_id,
        title=payload.title, description=payload.description, quantity=payload.quantity,
        budget=Decimal(str(payload.budget)) if payload.budget else None,
        required_by=required_by, status="OPEN",
    )
    db.add(req)
    db.flush()
    from app.core.events import bus, CUSTOM_REQUEST_CREATED

    bus.publish(CUSTOM_REQUEST_CREATED, {"request_id": req.id})
    notification_service.create(db, user_id=profile.user_id, type="CUSTOM_REQUEST",
                                title="Custom order request",
                                body=f"{payload.title} — see details and respond with a quote.",
                                link="/artisan/orders")
    return {"id": req.id, "status": req.status}


@router.get("/custom-requests/mine", summary="My custom requests (buyer)")
def my_custom(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(CustomRequest).filter(CustomRequest.buyer_id == user.id).order_by(CustomRequest.created_at.desc()).all()
    return {"items": [_custom_json(r) for r in rows]}


@router.get("/custom-requests/artisan", summary="Custom requests for my studio (artisan)",
            dependencies=[Depends(require_roles("ARTISAN", "ADMIN"))])
def artisan_custom(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
    if profile is None:
        return {"items": []}
    rows = (
        db.query(CustomRequest)
        .filter(CustomRequest.artisan_id == profile.id)
        .order_by(CustomRequest.created_at.desc())
        .all()
    )
    return {"items": [_custom_json(r) for r in rows]}


def _custom_json(r: CustomRequest) -> dict:
    return {
        "id": r.id, "title": r.title, "description": r.description, "quantity": r.quantity,
        "budget": float(r.budget) if r.budget else None,
        "required_by": r.required_by.isoformat() if r.required_by else None,
        "status": r.status, "created_at": r.created_at.isoformat(),
    }


# -------------------------------------------------------------------- quotes

@router.post("/quotes", summary="Quote a bulk or custom request (artisan)",
             dependencies=[Depends(require_roles("ARTISAN", "ADMIN"))])
def create_quote(payload: QuoteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    quote = request_service.create_quote(
        db, artisan_user=user, request_type=payload.request_type, request_id=payload.request_id,
        unit_price=Decimal(str(payload.unit_price)), lead_time_days=payload.lead_time_days,
        note=payload.note, quantity=payload.quantity,
    )
    return {"id": quote.id, "total": float(quote.total), "status": quote.status}


@router.get("/quotes/mine", summary="Quotes on my requests (buyer)")
def my_quotes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bulk_ids = [r.id for r in db.query(BulkRequest).filter(BulkRequest.buyer_id == user.id).all()]
    custom_ids = [r.id for r in db.query(CustomRequest).filter(CustomRequest.buyer_id == user.id).all()]
    rows = []
    if bulk_ids:
        rows += db.query(Quote).filter(Quote.request_type == "BULK", Quote.request_id.in_(bulk_ids)).all()
    if custom_ids:
        rows += db.query(Quote).filter(Quote.request_type == "CUSTOM", Quote.request_id.in_(custom_ids)).all()
    def _artisan_name(q: Quote) -> str:
        p = db.query(ArtisanProfile).filter(ArtisanProfile.id == q.artisan_id).first()
        return p.display_name if p else "Artisan"
    return {"items": [
        {"id": q.id, "request_type": q.request_type, "request_id": q.request_id,
         "artisan": _artisan_name(q), "unit_price": float(q.unit_price), "quantity": q.quantity,
         "total": float(q.total), "lead_time_days": q.lead_time_days, "note": q.note,
         "status": q.status, "expires_at": q.expires_at.isoformat() if q.expires_at else None}
        for q in rows
    ]}


@router.post("/quotes/{quote_id}/accept", summary="Accept a quote → creates the order")
def accept_quote(quote_id: str, payload: AcceptQuoteIn,
                 user: User = Depends(require_roles("BUYER", "B2B_BUYER", "ADMIN")),
                 db: Session = Depends(get_db)):
    return request_service.accept_quote(db, buyer=user, quote_id=quote_id, address=payload.shipping_address)


# ------------------------------------------------------------ notifications

@router.get("/notifications", summary="My notifications")
def notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = notification_service.list_for(db, user.id)
    return {"items": [
        {"id": n.id, "type": n.type, "title": n.title, "body": n.body, "link": n.link,
         "is_read": n.is_read, "created_at": n.created_at.isoformat()} for n in rows
    ]}


@router.patch("/notifications/{notification_id}/read", summary="Mark a notification read")
def mark_read(notification_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification_service.mark_read(db, user.id, notification_id)
    return {"read": True}
