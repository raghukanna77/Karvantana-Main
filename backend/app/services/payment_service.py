"""Payment architecture (blueprint §28, §53).

PaymentProvider interface with a clearly-labeled DemoPaymentProvider (sandbox)
and a Razorpay-shaped provider slot. Server-side verification only: the client
"success" is never trusted; webhook signature + idempotency settle payments.
"""

from __future__ import annotations

import hmac
import hashlib
import secrets
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.core.events import bus, PAYMENT_CONFIRMED, PAYMENT_FAILED
from app.models.commerce import Order, OrderStatus, Payment, Refund
from app.services.notification_service import notification_service


class PaymentProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def create_intent(self, *, order: Order, amount: Decimal, currency: str) -> dict:
        """Return {provider_payment_id, checkout_url?, demo: bool}."""

    @abstractmethod
    def verify_webhook(self, *, payload_body: bytes, signature: Optional[str], secret: str) -> bool: ...

    @abstractmethod
    def refund(self, *, provider_payment_id: str, amount: Decimal) -> dict: ...


class DemoPaymentProvider(PaymentProvider):
    """SANDBOX provider — deterministic, clearly labeled, no real money."""

    name = "demo"

    def create_intent(self, *, order: Order, amount: Decimal, currency: str) -> dict:
        return {
            "provider_payment_id": f"demo_pay_{secrets.token_hex(8)}",
            "demo": True,
            "checkout_url": None,
        }

    def verify_webhook(self, *, payload_body: bytes, signature: Optional[str], secret: str) -> bool:
        expected = hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
        return bool(signature) and hmac.compare_digest(expected, signature)

    def refund(self, *, provider_payment_id: str, amount: Decimal) -> dict:
        return {"provider_refund_id": f"demo_ref_{secrets.token_hex(8)}", "status": "COMPLETED"}


class RazorpayProvider(PaymentProvider):
    """Production slot — requires RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET."""

    name = "razorpay"

    def __init__(self) -> None:
        if not get_settings().is_production:
            pass  # enabled explicitly via settings in production

    def create_intent(self, *, order: Order, amount: Decimal, currency: str) -> dict:
        raise NotImplementedError("Configure Razorpay credentials to enable live payments.")

    def verify_webhook(self, *, payload_body: bytes, signature: Optional[str], secret: str) -> bool:
        expected = hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
        return bool(signature) and hmac.compare_digest(expected, signature)

    def refund(self, *, provider_payment_id: str, amount: Decimal) -> dict:
        raise NotImplementedError("Configure Razorpay credentials to enable live refunds.")


_PROVIDER: dict[str, PaymentProvider] = {}


def get_payment_provider() -> PaymentProvider:
    name = get_settings().PAYMENT_PROVIDER
    if name not in _PROVIDER:
        _PROVIDER[name] = DemoPaymentProvider() if name == "demo" else RazorpayProvider()
    return _PROVIDER[name]


class PaymentService:
    def create_intent(self, db: Session, *, order: Order, idempotency_key: Optional[str] = None) -> dict:
        if order.status not in (OrderStatus.PENDING_PAYMENT, OrderStatus.DRAFT):
            raise ConflictError("This order is not awaiting payment.")
        if idempotency_key:
            existing = db.query(Payment).filter(Payment.idempotency_key == idempotency_key).first()
            if existing:
                return {"payment_id": existing.id, "provider": existing.provider, "amount": float(existing.amount), "demo": existing.provider == "demo"}
        provider = get_payment_provider()
        intent = provider.create_intent(order=order, amount=order.total, currency=order.currency)
        payment = Payment(
            order_id=order.id,
            provider=provider.name,
            provider_payment_id=intent["provider_payment_id"],
            amount=order.total,
            currency=order.currency,
            status="CREATED",
            idempotency_key=idempotency_key,
        )
        db.add(payment)
        db.flush()
        return {
            "payment_id": payment.id,
            "provider": provider.name,
            "provider_payment_id": intent["provider_payment_id"],
            "amount": float(order.total),
            "currency": order.currency,
            "demo": intent.get("demo", False),
        }

    # --------------------------------------------------------------- settle

    def settle_webhook(self, db: Session, *, provider_payment_id: str, event: str,
                       signature: Optional[str], raw_body: bytes) -> dict:
        provider = get_payment_provider()
        secret = get_settings().JWT_SECRET + ":payments"  # demo secret; real provider secret via env
        if not provider.verify_webhook(payload_body=raw_body, signature=signature, secret=secret):
            raise ValidationFailedError("Invalid webhook signature.", code="WEBHOOK_SIGNATURE_INVALID")

        payment = db.query(Payment).filter(Payment.provider_payment_id == provider_payment_id).first()
        if payment is None:
            raise NotFoundError("Unknown payment reference.")

        # Idempotent: replayed events are acknowledged, not re-applied.
        if payment.status == "CAPTURED" and event == "payment.captured":
            return {"status": "already_processed"}
        if payment.status == "FAILED" and event == "payment.failed":
            return {"status": "already_processed"}

        order = db.query(Order).filter(Order.id == payment.order_id).first()
        if event == "payment.captured":
            payment.status = "CAPTURED"
            order.status = OrderStatus.CONFIRMED
            db.add(_history(order, None, OrderStatus.CONFIRMED))
            bus.publish(PAYMENT_CONFIRMED, {"order_id": order.id})
            notification_service.create(db, user_id=order.buyer_id, type="PAYMENT_RECEIVED",
                                        title="Payment successful",
                                        body=f"We received your payment for {order.order_number}.",
                                        link=f"/orders/{order.id}")
            self._notify_artisan(db, order)
        elif event == "payment.failed":
            payment.status = "FAILED"
            bus.publish(PAYMENT_FAILED, {"order_id": order.id})
        db.flush()
        return {"status": "processed", "order_status": order.status}

    def _notify_artisan(self, db: Session, order: Order) -> None:
        from app.models.commerce import OrderItem
        from app.models.profile import ArtisanProfile

        item = db.query(OrderItem).filter(OrderItem.order_id == order.id).first()
        if not item:
            return
        profile = db.query(ArtisanProfile).filter(ArtisanProfile.id == item.artisan_id).first()
        if profile:
            notification_service.create(db, user_id=profile.user_id, type="PAYMENT_RECEIVED",
                                        title="Payment received",
                                        body=f"Payment for order {order.order_number} is confirmed. You can start crafting.",
                                        link=f"/artisan/orders/{order.id}")

    # --------------------------------------------------------------- refund

    def refund(self, db: Session, *, order: Order, amount: Decimal, reason: str, actor: User) -> dict:
        if actor.role != "ADMIN" and actor.id != order.buyer_id:
            from app.core.errors import PermissionDeniedError

            raise PermissionDeniedError("Only the buyer or an admin can request a refund.")
        payment = db.query(Payment).filter(Payment.order_id == order.id, Payment.status == "CAPTURED").first()
        if payment is None:
            raise ConflictError("No captured payment found for this order.")
        provider = get_payment_provider()
        result = provider.refund(provider_payment_id=payment.provider_payment_id, amount=amount)
        refund = Refund(
            payment_id=payment.id, provider_refund_id=result["provider_refund_id"],
            amount=amount, reason=reason[:300], status=result["status"],
        )
        db.add(refund)
        payment.status = "REFUNDED"
        db.flush()
        return {"refund_id": refund.id, "status": refund.status}


def _history(order: Order, from_status: Optional[str], to_status: str) -> OrderStatusHistory:
    from app.models.commerce import OrderStatusHistory

    return OrderStatusHistory(order_id=order.id, from_status=from_status, to_status=to_status, changed_by=None)
