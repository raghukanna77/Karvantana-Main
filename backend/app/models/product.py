"""Product catalogue: products, images, confidence-tagged attributes, variants.

Money columns use Numeric(12,2). Product images reference object storage URLs
(local media dir in dev, S3 in production) — never large blobs in the DB.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin, utcnow


class ProductLifecycle:
    DRAFT = "DRAFT"
    AI_PROCESSING = "AI_PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    PUBLISHED = "PUBLISHED"
    PAUSED = "PAUSED"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    ARCHIVED = "ARCHIVED"

    ALL = (DRAFT, AI_PROCESSING, REVIEW_REQUIRED, PUBLISHED, PAUSED, OUT_OF_STOCK, ARCHIVED)


class Product(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "products"
    __table_args__ = (Index("ix_products_lifecycle_price", "lifecycle", "price"),)

    artisan_id: Mapped[str] = mapped_column(ForeignKey("artisan_profiles.id"), index=True)
    category_id: Mapped[Optional[str]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    craft_type_id: Mapped[Optional[str]] = mapped_column(ForeignKey("craft_types.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(250), default="")
    short_description: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    craft_story: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    material: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    technique: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    colour: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    origin: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    usage: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    dimensions: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    weight_grams: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    production_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    inventory_mode: Mapped[str] = mapped_column(String(20), default="STOCK")  # STOCK|MADE_TO_ORDER|PRE_ORDER|CUSTOM
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=2)
    moq: Mapped[int] = mapped_column(Integer, default=1)  # minimum order quantity
    bulk_moq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bulk_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    customization_available: Mapped[bool] = mapped_column(Boolean, default=False)

    lifecycle: Mapped[str] = mapped_column(String(20), default=ProductLifecycle.DRAFT, index=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_catalogue_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    keywords: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # comma-separated

    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    images: Mapped[list["ProductImage"]] = relationship(  # noqa: F821
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )
    attributes: Mapped[list["ProductAttribute"]] = relationship(  # noqa: F821
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def effective_stock(self) -> int:
        if self.inventory_mode in ("MADE_TO_ORDER", "CUSTOM", "PRE_ORDER"):
            return 9999
        return self.stock_quantity


class ProductImage(UUIDPkMixin, Base):
    __tablename__ = "product_images"

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    original_url: Mapped[str] = mapped_column(String(500))
    enhanced_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quality_flags: Mapped[Optional[dict]] = mapped_column(JSON_TYPE := __import__("sqlalchemy").JSON, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    product: Mapped["Product"] = relationship(back_populates="images")  # noqa: F821


class ProductAttribute(UUIDPkMixin, Base):
    """Confidence-tagged structured field: {value, confidence, source}."""

    __tablename__ = "product_attributes"
    __table_args__ = (UniqueConstraint("product_id", "field_key", name="uq_product_attribute"),)

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    field_key: Mapped[str] = mapped_column(String(60))
    value: Mapped[str] = mapped_column(String(500))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(20), default="ARTISAN_INPUT")  # VOICE|IMAGE|ARTISAN_INPUT|AI_INFERENCE|SYSTEM

    product: Mapped["Product"] = relationship(back_populates="attributes")  # noqa: F821


class ProductVariant(UUIDPkMixin, Base):
    __tablename__ = "product_variants"

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    attributes: Mapped[Optional[dict]] = mapped_column(__import__("sqlalchemy").JSON, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
