"""Payment endpoints (/api/v1/payments)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models.commerce import Order
from app.models.user import User
from app.security.dependencies import get_current_user, require_roles
from app.services.order_service import order_service
from app.services.payment_service import PaymentService, get_payment_provider

router = APIRouter(prefix="/payments", tags=["payments"])
payment_service = PaymentService()


@router.post("/create-intent", summary="Create a payment intent for an order")
def create_intent(payload: dict, idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
                  user: User = Depends(require_roles("BUYER", "B2B_BUYER", "ADMIN")),
                  db: Session = Depends(get_db)):
    order = order_service.get_order_for(db, str(payload.get("order_id", "")), user)
    return payment_service.create_intent(db, order=order, idempotency_key=idempotency_key)


@router.post("/demo/confirm", summary="Sandbox: confirm a demo payment (DEMO provider only)")
def demo_confirm(payload: dict, user: User = Depends(require_roles("BUYER", "B2B_BUYER", "ADMIN")),
                 db: Session = Depends(get_db)):
    """Demo-mode settlement ONLY — simulates the gateway calling our webhook.
    The signature is computed here exactly as the provider would; live
    integrations receive this from the gateway's infrastructure instead."""
    if get_payment_provider().name != "demo":
        from app.core.errors import ValidationFailedError

        raise ValidationFailedError("Demo payments are only available in demo mode.")
    provider_payment_id = str(payload.get("provider_payment_id", ""))
    payment = payment_service_settle(db, provider_payment_id, "payment.captured")
    return payment


def payment_service_settle(db: Session, provider_payment_id: str, event: str) -> dict:
    from app.services.payment_service import PaymentService as PS

    # Demo only: sign with the same secret the webhook verifier expects.
    import hmac as _hmac
    import hashlib as _hashlib

    from app.core.config import get_settings

    secret = get_settings().JWT_SECRET + ":payments"
    body = provider_payment_id.encode()
    signature = _hmac.new(secret.encode(), body, _hashlib.sha256).hexdigest()
    return payment_service.settle_webhook(db, provider_payment_id=provider_payment_id,
                                          event=event, signature=signature, raw_body=body)


@router.post("/webhook", summary="Provider webhook (signature-verified, idempotent)")
async def webhook(request: Request, db: Session = Depends(get_db),
                  x_signature: Optional[str] = Header(default=None, alias="X-Signature")):
    raw = await request.body()
    payload = await request.json()
    provider_payment_id = str(payload.get("provider_payment_id", ""))
    event = str(payload.get("event", ""))
    if not provider_payment_id or not event:
        from app.core.errors import ValidationFailedError

        raise ValidationFailedError("Malformed webhook payload.")
    return payment_service.settle_webhook(db, provider_payment_id=provider_payment_id,
                                          event=event, signature=x_signature, raw_body=raw)


@router.post("/refunds", summary="Request a refund (buyer or admin)")
def create_refund(payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from decimal import Decimal

    order = order_service.get_order_for(db, str(payload.get("order_id", "")), user)
    amount = Decimal(str(payload.get("amount", 0))) or order.total
    reason = str(payload.get("reason", "Buyer requested"))
    return payment_service.refund(db, order=order, amount=amount, reason=reason, actor=user)
