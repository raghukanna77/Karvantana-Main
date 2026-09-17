"""Engagement models: reviews, reputation, follows, saves, notifications, messages, disputes."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, UUIDPkMixin, utcnow


class Review(UUIDPkMixin, TimestampMixin, Base):
    """Verified-purchase review — only created after a COMPLETED order (gated in service)."""

    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("order_item_id", name="uq_review_order_item"),)

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    artisan_id: Mapped[str] = mapped_column(String(36), index=True)  # artisan_profiles.id
    buyer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    order_item_id: Mapped[str] = mapped_column(ForeignKey("order_items.id"), unique=True)
    product_rating: Mapped[int] = mapped_column(Integer)
    quality_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    communication_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    value_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    delivery_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified_purchase: Mapped[bool] = mapped_column(Boolean, default=True)

    buyer: Mapped["User"] = relationship("User", lazy="joined")  # noqa: F821


class ArtisanReputation(UUIDPkMixin, Base):
    """Rolling reputation aggregates; broader than a star rating (blueprint §24/§125)."""

    __tablename__ = "artisan_reputation"

    artisan_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)  # artisan_profiles.id
    rating_avg: Mapped[float] = mapped_column(Float, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    verified_orders: Mapped[int] = mapped_column(Integer, default=0)
    repeat_buyers: Mapped[int] = mapped_column(Integer, default=0)
    response_rate: Mapped[float] = mapped_column(Float, default=1.0)
    on_time_fulfilment_rate: Mapped[float] = mapped_column(Float, default=1.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Follow(UUIDPkMixin, Base):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("user_id", "artisan_id", name="uq_follow"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    artisan_id: Mapped[str] = mapped_column(String(36), index=True)  # artisan_profiles.id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SavedArtisan(UUIDPkMixin, Base):
    __tablename__ = "saved_artisans"
    __table_args__ = (UniqueConstraint("user_id", "artisan_id", name="uq_saved_artisan"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    artisan_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SavedProduct(UUIDPkMixin, Base):
    __tablename__ = "saved_products"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_saved_product"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Notification(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notif_user_read", "user_id", "is_read"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))  # ORDER_RECEIVED|PAYMENT_RECEIVED|BULK_ENQUIRY|AI_CATALOGUE_READY|...
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    link: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)  # deep link path
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class Message(UUIDPkMixin, TimestampMixin, Base):
    """Threaded messages between buyer and artisan (scoped, never public)."""

    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_thread", "thread_key", "created_at"),)

    thread_key: Mapped[str] = mapped_column(String(80), index=True)  # e.g. "custom:{request_id}"
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    recipient_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)


class Dispute(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "disputes"

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    raised_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(String(300))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)  # OPEN|UNDER_REVIEW|RESOLVED|REJECTED|ESCALATED
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
