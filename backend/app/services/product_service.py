"""Product service: lifecycle management, ownership-enforced queries."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationFailedError
from app.models.catalog import Category, CraftType
from app.models.product import Product, ProductAttribute, ProductImage, ProductLifecycle
from app.models.profile import ArtisanProfile
from app.models.user import User

MAX_IMAGES_PER_PRODUCT = 8


class ProductService:
    # ------------------------------------------------------------- queries

    def get_owned_product(self, db: Session, product_id: str, user: User) -> Product:
        product = self.get_product(db, product_id)
        profile = self._profile_for(db, user)
        if product.artisan_id != profile.id and user.role != "ADMIN":
            raise PermissionDeniedError("You can only manage your own products.")
        return product

    def get_product(self, db: Session, product_id: str) -> Product:
        product = (
            db.query(Product)
            .options(joinedload(Product.images), joinedload(Product.attributes))
            .filter(Product.id == product_id, Product.deleted_at.is_(None))
            .first()
        )
        if product is None:
            raise NotFoundError("This product no longer exists.")
        return product

    def artisan_products(self, db: Session, artisan_id: str, lifecycle: Optional[str] = None) -> list[Product]:
        q = db.query(Product).filter(Product.artisan_id == artisan_id, Product.deleted_at.is_(None))
        if lifecycle:
            q = q.filter(Product.lifecycle == lifecycle)
        return q.order_by(Product.updated_at.desc()).all()

    def _profile_for(self, db: Session, user: User) -> ArtisanProfile:
        profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
        if profile is None:
            raise PermissionDeniedError("Complete artisan onboarding first.")
        return profile

    # --------------------------------------------------------------- create

    def create_product(
        self,
        db: Session,
        *,
        user: User,
        title: str = "",
        category_id: Optional[str] = None,
        craft_type_id: Optional[str] = None,
        **fields,
    ) -> Product:
        profile = self._profile_for(db, user)
        allowed = {
            "short_description", "description", "craft_story", "material", "technique",
            "colour", "origin", "usage", "dimensions", "weight_grams", "production_days",
            "inventory_mode", "stock_quantity", "low_stock_threshold", "moq",
            "bulk_moq", "bulk_price", "customization_available", "price", "keywords",
        }
        product = Product(
            artisan_id=profile.id,
            title=(title or "")[:250],
            category_id=category_id,
            craft_type_id=craft_type_id,
            **{k: v for k, v in fields.items() if k in allowed},
        )
        if product.price is None:
            product.price = Decimal("0")
        db.add(product)
        db.flush()
        return product

    def update_product(self, db: Session, product: Product, changes: dict) -> Product:
        allowed = {
            "title", "short_description", "description", "craft_story", "material",
            "technique", "colour", "origin", "usage", "dimensions", "weight_grams",
            "production_days", "inventory_mode", "stock_quantity", "low_stock_threshold",
            "moq", "bulk_moq", "bulk_price", "customization_available", "price", "keywords",
            "category_id", "craft_type_id", "lifecycle",
        }
        for key, value in changes.items():
            if key in allowed and value is not None:
                setattr(product, key, value)
        db.flush()
        return product

    # ------------------------------------------------------------- lifecycle

    def publish(self, db: Session, product: Product) -> Product:
        problems = []
        if not (product.title or "").strip():
            problems.append("Add a product title.")
        if product.price is None or Decimal(product.price) <= 0:
            problems.append("Set a price above ₹0.")
        if not product.images:
            problems.append("Add at least one photo.")
        if problems:
            raise ValidationFailedError("; ".join(problems), code="PUBLISH_INCOMPLETE", details={"missing": problems})
        product.lifecycle = ProductLifecycle.PUBLISHED
        product.published_at = utcnow_import()
        db.flush()
        return product

    def soft_delete(self, db: Session, product: Product) -> None:
        product.deleted_at = utcnow_import()
        product.lifecycle = ProductLifecycle.ARCHIVED
        db.flush()

    # ---------------------------------------------------------------- media

    def add_image(self, db: Session, product: Product, *, url: str, mime: Optional[str],
                  size: Optional[int], quality_score: Optional[float] = None,
                  enhanced_url: Optional[str] = None, width: Optional[int] = None,
                  height: Optional[int] = None) -> ProductImage:
        if len(product.images) >= MAX_IMAGES_PER_PRODUCT:
            raise ValidationFailedError(f"Up to {MAX_IMAGES_PER_PRODUCT} photos per product.", code="TOO_MANY_IMAGES")
        is_primary = len(product.images) == 0
        img = ProductImage(
            product_id=product.id, original_url=url, mime_type=mime, size_bytes=size,
            quality_score=quality_score, enhanced_url=enhanced_url,
            is_primary=is_primary, position=len(product.images),
        )
        db.add(img)
        db.flush()
        return img

    def set_attributes(self, db: Session, product: Product, attrs: dict[str, dict]) -> None:
        """attrs: {field_key: {value, confidence, source}} — upsert, artisan-corrected values win."""
        for key, payload in attrs.items():
            if not isinstance(payload, dict) or "value" not in payload:
                continue
            value = payload["value"]
            if value in (None, ""):
                continue
            row = next((a for a in product.attributes if a.field_key == key), None)
            if row is None:
                row = ProductAttribute(product_id=product.id, field_key=key)
                db.add(row)
            row.value = str(value)[:500]
            row.confidence = float(payload.get("confidence", 1.0))
            # ARTISAN_INPUT always outranks AI sources; never downgrade a human correction.
            source = payload.get("source", "AI_INFERENCE")
            existing = row.source if row.source else None
            if existing == "ARTISAN_INPUT" and source != "ARTISAN_INPUT":
                continue
            row.source = source
        db.flush()

    def resolve_category(self, db: Session, category_name: Optional[str]) -> Optional[str]:
        if not category_name:
            return None
        cat = db.query(Category).filter(Category.name == category_name).first()
        if cat is None:
            cat = Category(name=category_name, slug=category_name.lower().replace(" ", "-"))
            db.add(cat)
            db.flush()
        return cat.id


def utcnow_import():
    from app.models import utcnow

    return utcnow()


product_service = ProductService()
