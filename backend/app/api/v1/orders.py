"""Order endpoints (/api/v1/orders)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.product import OrderCreateIn, OrderStatusIn
from app.security.dependencies import get_current_user, require_roles
from app.services.order_service import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", summary="Create an order (idempotent)")
def create_order(payload: OrderCreateIn, request: Request,
                 response_model=None,
                 idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
                 user: User = Depends(require_roles("BUYER", "B2B_BUYER", "ADMIN")),
                 db: Session = Depends(get_db)):
    order = order_service.create_order(
        db, buyer=user, items=payload.items, shipping_address=payload.shipping_address,
        buyer_note=payload.buyer_note, idempotency_key=idempotency_key,
    )
    return _order_json(order)


@router.get("/mine", summary="My orders (buyer)")
def my_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": [_order_json(o) for o in order_service.buyer_orders(db, user.id)]}


@router.get("/artisan", summary="Orders for my studio (artisan)",
            dependencies=[Depends(require_roles("ARTISAN", "ADMIN"))])
def artisan_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models.profile import ArtisanProfile

    profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
    if profile is None:
        return {"items": []}
    return {"items": [_order_json(o) for o in order_service.artisan_orders(db, profile.id)]}


@router.get("/{order_id}", summary="Order detail (buyer, artisan or admin)")
def get_order(order_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = order_service.get_order_for(db, order_id, user)
    return _order_json(order, include_history=True)


@router.post("/{order_id}/status", summary="Move an order to the next status")
def change_status(order_id: str, payload: OrderStatusIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    order = order_service.get_order_for(db, order_id, user)
    order_service.transition(db, order, payload.status, actor=user, note=payload.note)
    return _order_json(order, include_history=True)


@router.post("/{order_id}/reorder", summary="Buy again from this artisan")
def reorder(order_id: str, user: User = Depends(require_roles("BUYER", "B2B_BUYER", "ADMIN")),
            db: Session = Depends(get_db)):
    order = order_service.get_order_for(db, order_id, user)
    new_order = order_service.reorder(db, order, user)
    return _order_json(new_order)


def _order_json(order, include_history: bool = False) -> dict:
    from app.models.commerce import OrderStatus

    data = {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "status_label": OrderStatus.LABELS.get(order.status, order.status),
        "subtotal": float(order.subtotal),
        "shipping_fee": float(order.shipping_fee),
        "platform_fee": float(order.platform_fee),
        "total": float(order.total),
        "currency": order.currency,
        "is_bulk": order.is_bulk,
        "created_at": order.created_at.isoformat(),
        "shipping_address": order.shipping_address,
        "items": [
            {
                "id": i.id,
                "product_id": i.product_id,
                "artisan_id": i.artisan_id,
                "title": i.product_title_snapshot,
                "image_url": i.product_image_url,
                "unit_price": float(i.unit_price),
                "quantity": i.quantity,
                "line_total": float(i.line_total),
            }
            for i in order.items
        ],
    }
    if include_history:
        data["history"] = [
            {"from": h.from_status, "to": h.to_status, "at": h.created_at.isoformat(), "note": h.note}
            for h in sorted(order.status_history, key=lambda h: h.created_at)
        ]
    return data
