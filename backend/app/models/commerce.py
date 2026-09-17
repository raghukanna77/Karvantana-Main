"""Commerce models: orders, payments, refunds, shipments, quotes, bulk/custom requests."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, UUIDPkMixin, utcnow


class OrderStatus:
    DRAFT = "DRAFT"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    IN_PRODUCTION = "IN_PRODUCTION"
    READY_TO_SHIP = "READY_TO_SHIP"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    RETURN_REQUESTED = "RETURN_REQUESTED"
    RETURNED = "RETURNED"
    REFUNDED = "REFUNDED"

    ALL = (
        DRAFT, PENDING_PAYMENT, CONFIRMED, PROCESSING, IN_PRODUCTION,
        READY_TO_SHIP, SHIPPED, DELIVERED, COMPLETED, CANCELLED,
        RETURN_REQUESTED, RETURNED, REFUNDED,
    )

    # buyer/artisan-facing simple labels
    LABELS = {
        DRAFT: "Draft",
        PENDING_PAYMENT: "Awaiting payment",
        CONFIRMED: "Confirmed",
        PROCESSING: "Being prepared",
        IN_PRODUCTION: "Being crafted",
        READY_TO_SHIP: "Ready to ship",
        SHIPPED: "Shipped",
        DELIVERED: "Delivered",
        COMPLETED: "Completed",
        CANCELLED: "Cancelled",
        RETURN_REQUESTED: "Return requested",
        RETURNED: "Returned",
        REFUNDED: "Refunded",
    }

    # legal artisan transitions
    ARTISAN_TRANSITIONS: dict[str, tuple[str, ...]] = {
        CONFIRMED: (PROCESSING, IN_PRODUCTION, CANCELLED),
        PROCESSING: (IN_PRODUCTION, READY_TO_SHIP, CANCELLED),
        IN_PRODUCTION: (READY_TO_SHIP, CANCELLED),
        READY_TO_SHIP: (SHIPPED, CANCELLED),
        SHIPPED: (DELIVERED,),
        DELIVERED: (COMPLETED, RETURN_REQUESTED),
        RETURN_REQUESTED: (RETURNED, COMPLETED),
        RETURNED: (REFUNDED, COMPLETED),
    }

    # buyer cancellations allowed until production starts
    BUYER_TRANSITIONS: dict[str, tuple[str, ...]] = {
        PENDING_PAYMENT: (CANCELLED,),
        CONFIRMED: (CANCELLED,),
        PROCESSING: (CANCELLED,),
    }


class Order(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (Index("ix_orders_buyer_status", "buyer_id", "status"),)

    order_number: Mapped[str] = mapped_column(String(20), unique=True)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default=OrderStatus.DRAFT, index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    platform_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(80), unique=True, nullable=True)
    shipping_address: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    buyer_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_bulk: Mapped[bool] = mapped_column(Boolean, default=False)
    related_request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    payment_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderItem(UUIDPkMixin, Base):
    __tablename__ = "order_items"

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    artisan_id: Mapped[str] = mapped_column(String(36), index=True)  # artisan_profiles.id snapshot
    product_title_snapshot: Mapped[str] = mapped_column(String(250))
    product_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    order: Mapped["Order"] = relationship(back_populates="items")


class OrderStatusHistory(UUIDPkMixin, Base):
    __tablename__ = "order_status_history"

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    from_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30))
    changed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    order: Mapped["Order"] = relationship(back_populates="status_history")


class Payment(UUIDPkMixin, Base):
    __tablename__ = "payments"

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30))  # demo | razorpay
    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[str] = mapped_column(String(20), default="CREATED", index=True)  # CREATED|AUTHORIZED|CAPTURED|FAILED|REFUNDED
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(80), unique=True, nullable=True)
    meta_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Refund(UUIDPkMixin, Base):
    __tablename__ = "refunds"

    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), index=True)
    provider_refund_id: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reason: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PROCESSING")  # PROCESSING|COMPLETED|FAILED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Shipment(UUIDPkMixin, Base):
    __tablename__ = "shipments"

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30), default="demo")
    tracking_number: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="LABEL_CREATED")  # LABEL_CREATED|PICKED_UP|IN_TRANSIT|OUT_FOR_DELIVERY|DELIVERED|CANCELLED
    estimated_delivery: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TrackingEvent(UUIDPkMixin, Base):
    __tablename__ = "tracking_events"

    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    location: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class QuoteStatus:
    PENDING = "PENDING"
    VIEWED = "VIEWED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"


class Quote(UUIDPkMixin, TimestampMixin, Base):
    """Artisan quote against a bulk or custom request; acceptance creates an order."""

    __tablename__ = "quotes"

    request_type: Mapped[str] = mapped_column(String(10))  # BULK | CUSTOM
    request_id: Mapped[str] = mapped_column(String(36), index=True)  # bulk_requests.id or custom_requests.id
    artisan_id: Mapped[str] = mapped_column(String(36), index=True)  # artisan_profiles.id
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=QuoteStatus.PENDING, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class BulkRequest(UUIDPkMixin, TimestampMixin, Base):
    """B2B bulk requirement (AI-parsed from natural language)."""

    __tablename__ = "bulk_requests"

    buyer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category_hint: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    max_unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    required_by: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    customization_required: Mapped[bool] = mapped_column(Boolean, default=False)
    parsed_requirements: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # AI parse output
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)  # OPEN|QUOTING|ORDERED|CLOSED
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # user id


class CustomRequest(UUIDPkMixin, TimestampMixin, Base):
    """Buyer custom-order request to a specific artisan."""

    __tablename__ = "custom_requests"

    buyer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    artisan_id: Mapped[str] = mapped_column(String(36), index=True)  # artisan_profiles.id
    product_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # inspiration product
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    budget: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    required_by: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)  # OPEN|QUOTING|ORDERED|DECLINED|CLOSED
