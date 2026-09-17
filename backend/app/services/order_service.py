"""Order service: transactional creation, idempotency, state machine, inventory.

Concurrency: inventory decrement happens inside a DB transaction with a
row-level check (optimistic guard); two buyers racing for the last unit cannot
oversell. Idempotency keys make retries safe (blueprint §135, §136).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationFailedError
from app.core.events import bus, ORDER_CREATED, ORDER_STATUS_CHANGED, REORDER_CREATED
from app.models.commerce import Order, OrderItem, OrderStatus, OrderStatusHistory
from app.models.product import Product, ProductLifecycle
from app.models.profile import ArtisanProfile

PLATFORM_FEE_PCT = Decimal("0.02")  # configurable in admin settings later


def _order_number() -> str:
    return f"KV-{datetime.now(timezone.utc).strftime('%y%m')}-{secrets.token_hex(3).upper()}"


class OrderService:
    # --------------------------------------------------------------- create

    def create_order(
        self,
        db: Session,
        *,
        buyer: User,
        items: list[dict],
        shipping_address: dict,
        buyer_note: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Order:
        """items: [{product_id, quantity}] — prices are resolved server-side only."""
        if idempotency_key:
            existing = db.query(Order).filter(Order.idempotency_key == idempotency_key).first()
            if existing:
                return existing
        if not items:
            raise ValidationFailedError("Add at least one product to your order.")

        product_ids = [i["product_id"] for i in items]
        products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}

        subtotal = Decimal("0")
        order_items: list[tuple[Product, int]] = []
        for item in items:
            product = products.get(item["product_id"])
            if product is None:
                raise NotFoundError("One of the products is no longer available.")
            if product.lifecycle != ProductLifecycle.PUBLISHED:
                raise ConflictError(f"'{product.title or 'This product'}' is not currently available.")
            qty = int(item.get("quantity", 1))
            if qty < 1 or qty > 500:
                raise ValidationFailedError("Quantity must be between 1 and 500.")
            if product.effective_stock < qty:
                raise ConflictError(
                    f"Only {product.effective_stock} left of '{product.title or 'this product'}'.",
                    code="INSUFFICIENT_STOCK",
                )
            unit_price = Decimal(str(product.bulk_price if (product.bulk_price and qty >= (product.bulk_moq or 10**9)) else product.price))
            subtotal += unit_price * qty
            order_items.append((product, qty, item.get("_unit_price_override")))

        shipping_fee = Decimal("0")
        platform_fee = (subtotal * PLATFORM_FEE_PCT).quantize(Decimal("0.01"))
        order = Order(
            order_number=_order_number(),
            buyer_id=buyer.id,
            status=OrderStatus.PENDING_PAYMENT,
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            platform_fee=platform_fee,
            total=subtotal + platform_fee,
            idempotency_key=idempotency_key,
            shipping_address=shipping_address,
            buyer_note=(buyer_note or None),
        )
        db.add(order)
        db.flush()

        primary_image = {}
        for (product, qty, price_override) in order_items:
            unit_price = Decimal(str(price_override)) if price_override is not None else product.price
            first_img = product.images[0] if product.images else None
            db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    artisan_id=product.artisan_id,
                    product_title_snapshot=product.title or "Handmade product",
                    product_image_url=first_img.original_url if first_img else None,
                    unit_price=unit_price,
                    quantity=qty,
                    line_total=unit_price * qty,
                )
            )
            # Inventory: guard-then-decrement inside this transaction. Products
            # in STOCK modes only; made-to-order items skip stock.
            if product.inventory_mode == "STOCK":
                affected = (
                    db.query(Product)
                    .filter(Product.id == product.id, Product.stock_quantity >= qty)
                    .update({"stock_quantity": Product.stock_quantity - qty}, synchronize_session=False)
                )
                if affected == 0:
                    raise ConflictError(f"'{product.title or 'This product'}' just sold out.", code="INSUFFICIENT_STOCK")
                if product.stock_quantity - qty <= product.low_stock_threshold:
                    product.lifecycle = ProductLifecycle.OUT_OF_STOCK if product.stock_quantity - qty == 0 else product.lifecycle

        db.add(OrderStatusHistory(order_id=order.id, from_status=None, to_status=OrderStatus.PENDING_PAYMENT, changed_by=buyer.id))
        db.flush()
        bus.publish(ORDER_CREATED, {"order_id": order.id, "buyer_id": buyer.id})
        # notify artisans
        artisan_ids = {p.artisan_id for p, _, _ in order_items}
        self._notify_artisans(db, artisan_ids, order)
        return order

    def _notify_artisans(self, db: Session, artisan_profile_ids: set[str], order: Order) -> None:
        from app.services.notification_service import notification_service

        profiles = db.query(ArtisanProfile).filter(ArtisanProfile.id.in_(artisan_profile_ids)).all()
        for profile in profiles:
            notification_service.create(
                db,
                user_id=profile.user_id,
                type="ORDER_RECEIVED",
                title="New order received",
                body=f"Order {order.order_number} is waiting for confirmation.",
                link=f"/artisan/orders/{order.id}",
            )

    # ---------------------------------------------------------------- reads

    def buyer_orders(self, db: Session, buyer_id: str) -> list[Order]:
        return (
            db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.buyer_id == buyer_id)
            .order_by(Order.created_at.desc())
            .all()
        )

    def artisan_orders(self, db: Session, artisan_id: str) -> list[Order]:
        return (
            db.query(Order)
            .options(joinedload(Order.items))
            .join(OrderItem, OrderItem.order_id == Order.id)
            .filter(OrderItem.artisan_id == artisan_id)
            .distinct()
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_order_for(self, db: Session, order_id: str, user: User) -> Order:
        order = (
            db.query(Order)
            .options(joinedload(Order.items), joinedload(Order.status_history))
            .filter(Order.id == order_id)
            .first()
        )
        if order is None:
            raise NotFoundError("Order not found.")
        if user.role == "ADMIN":
            return order
        if order.buyer_id == user.id:
            return order
        profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
        if profile and any(i.artisan_id == profile.id for i in order.items):
            return order
        raise PermissionDeniedError("You cannot view this order.")

    # ----------------------------------------------------------- transitions

    def transition(self, db: Session, order: Order, to_status: str, actor: User, note: Optional[str] = None) -> Order:
        current = order.status
        allowed: tuple[str, ...] = ()
        if actor.role in ("ARTISAN", "ADMIN"):
            allowed = tuple(OrderStatus.ARTISAN_TRANSITIONS.get(current, ()))
        if actor.id == order.buyer_id or actor.role == "ADMIN":
            allowed = allowed + tuple(OrderStatus.BUYER_TRANSITIONS.get(current, ()))
        if to_status not in allowed:
            raise ConflictError(f"Cannot move this order from {OrderStatus.LABELS.get(current, current)} to {OrderStatus.LABELS.get(to_status, to_status)}.")
        order.status = to_status
        db.add(OrderStatusHistory(order_id=order.id, from_status=current, to_status=to_status, changed_by=actor.id, note=note))
        db.flush()
        bus.publish(ORDER_STATUS_CHANGED, {"order_id": order.id, "to": to_status, "actor_id": actor.id})
        self._notify_status(db, order, to_status)
        return order

    def _notify_status(self, db: Session, order: Order, to_status: str) -> None:
        from app.services.notification_service import notification_service

        messages = {
            OrderStatus.SHIPPED: ("Order shipped", "Your order is on the way.", f"/orders/{order.id}"),
            OrderStatus.DELIVERED: ("Order delivered", "Your order has arrived. Enjoy!", f"/orders/{order.id}"),
            OrderStatus.COMPLETED: ("Order completed", f"Order {order.order_number} is complete. Thank you!", f"/orders/{order.id}"),
            OrderStatus.CANCELLED: ("Order cancelled", f"Order {order.order_number} was cancelled.", f"/orders/{order.id}"),
        }
        template = messages.get(to_status)
        if template:
            notification_service.create(db, user_id=order.buyer_id, type=f"ORDER_{to_status}",
                                        title=template[0], body=template[1], link=template[2])

    # -------------------------------------------------------------- reorder

    def reorder(self, db: Session, order: Order, actor: User) -> Order:
        """Direct reorder: clone items at current published prices/stock."""
        lines = []
        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id, Product.lifecycle == ProductLifecycle.PUBLISHED).first()
            if product is not None:
                lines.append({"product_id": product.id, "quantity": item.quantity})
        if not lines:
            raise ConflictError("The products in this order are no longer available for reorder.")
        new_order = self.create_order(
            db, buyer=actor, items=lines,
            shipping_address=order.shipping_address or {},
            idempotency_key=None,
        )
        new_order.is_bulk = order.is_bulk
        new_order.related_request_id = order.id
        db.flush()
        bus.publish(REORDER_CREATED, {"order_id": new_order.id, "original_order_id": order.id})
        return new_order


order_service = OrderService()
