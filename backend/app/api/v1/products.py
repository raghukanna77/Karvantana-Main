"""Product endpoints (/api/v1/products) — artisan CRUD + public marketplace."""

from __future__ import annotations

import base64
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.errors import ValidationFailedError
from app.models.catalog import Category, CraftType
from app.models.product import Product, ProductLifecycle
from app.models.profile import ArtisanProfile
from app.models.user import User
from app.schemas.product import ProductCreateIn, ProductUpdateIn
from app.security.dependencies import get_current_user, get_optional_user, require_roles
from app.security.rate_limit import enforce
from app.services.analytics_service import analytics_service
from app.services.media_service import store_upload
from app.services.product_service import product_service

router = APIRouter(prefix="/products", tags=["products"])


def product_public(p: Product, include_attributes: bool = True) -> dict:
    primary = next((i for i in p.images if i.is_primary), p.images[0] if p.images else None)
    data = {
        "id": p.id,
        "title": p.title or "Handmade product",
        "short_description": p.short_description,
        "price": float(p.price or 0),
        "currency": p.currency,
        "image_url": (primary.enhanced_url or primary.original_url) if primary else None,
        "material": p.material,
        "technique": p.technique,
        "colour": p.colour,
        "origin": p.origin,
        "customization_available": p.customization_available,
        "bulk_moq": p.bulk_moq,
        "bulk_price": float(p.bulk_price) if p.bulk_price else None,
        "moq": p.moq,
        "production_days": p.production_days,
        "inventory_mode": p.inventory_mode,
        "in_stock": p.effective_stock > 0,
        "rating": None,
        "artisan_id": p.artisan_id,
    }
    if include_attributes:
        data["attributes"] = [
            {"key": a.field_key, "value": a.value, "confidence": a.confidence, "source": a.source}
            for a in p.attributes
        ]
    return data


@router.post("", summary="Create a product (draft)")
def create_product(payload: ProductCreateIn, user: User = Depends(require_roles("ARTISAN", "ADMIN")),
                   db: Session = Depends(get_db)):
    category_id = product_service.resolve_category(db, payload.category)
    product = product_service.create_product(
        db, user=user, title=payload.title, category_id=category_id,
        material=payload.material, technique=payload.technique, colour=payload.colour,
        origin=payload.origin, usage=payload.usage, dimensions=payload.dimensions,
        production_days=payload.production_days,
        price=payload.price, inventory_mode=payload.inventory_mode,
        stock_quantity=payload.stock_quantity, moq=payload.moq,
        bulk_moq=payload.bulk_moq,
        bulk_price=payload.bulk_price,
        customization_available=payload.customization_available,
    )
    product.lifecycle = ProductLifecycle.REVIEW_REQUIRED if payload.title else ProductLifecycle.DRAFT
    db.flush()
    return {"id": product.id, "lifecycle": product.lifecycle}


@router.get("/mine", summary="My products (artisan)", dependencies=[Depends(require_roles("ARTISAN", "ADMIN"))])
def my_products(lifecycle: Optional[str] = None, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
    if profile is None:
        return {"items": []}
    products = product_service.artisan_products(db, profile.id, lifecycle)
    return {"items": [{**product_public(p, include_attributes=False), "lifecycle": p.lifecycle} for p in products]}


@router.get("", summary="Marketplace listing with search + filters (public)")
def marketplace(
    request: Request,
    db: Session = Depends(get_db),
    q: Optional[str] = Query(default=None, max_length=200, description="Natural language or keyword search"),
    category: Optional[str] = None,
    material: Optional[str] = None,
    state: Optional[str] = None,
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    customizable: bool = False,
    bulk_available: bool = False,
    sort: str = Query(default="recent", pattern="^(recent|price_asc|price_desc|popular)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
):
    enforce("search", request.client.host if request.client else "anonymous")
    query = (
        db.query(Product)
        .options(joinedload(Product.images))
        .filter(Product.lifecycle == ProductLifecycle.PUBLISHED, Product.deleted_at.is_(None))
    )
    interpreted: dict = {}
    if q:
        # Structured interpretation of common natural patterns (blueprint §96)
        import re

        lowered = q.lower()
        budget = re.search(r"(?:under|below|upto|up to|less than)\s*₹?\s*(\d[\d,]*)", lowered)
        if budget:
            max_price = max_price or int(budget.group(1).replace(",", ""))
            interpreted["max_price"] = max_price
        qty = re.search(r"(\d[\d,]*)\s*(pieces|pcs|units|nos)?", lowered)
        if qty and ("pieces" in lowered or "pcs" in lowered or "units" in lowered):
            interpreted["quantity_hint"] = int(qty.group(1).replace(",", ""))
        states = ["tamil nadu", "kerala", "karnataka", "andhra pradesh", "telangana", "maharashtra",
                  "gujarat", "rajasthan", "odisha", "assam", "bengal", "bihar", "kashmir", "punjab"]
        for s in states:
            if s in lowered:
                state = state or s.title()
                interpreted["state"] = state
                break
        tokens = [w for w in re.split(r"\s+", lowered) if len(w) >= 3 and not w.isdigit()]
        if not tokens:
            tokens = [lowered.strip()]
        conds = []
        for tok in tokens:
            like = f"%{tok}%"
            conds.append(Product.title.ilike(like))
            conds.append(Product.description.ilike(like))
            conds.append(Product.material.ilike(like))
            conds.append(Product.keywords.ilike(like))
            conds.append(Product.technique.ilike(like))
            conds.append(Product.usage.ilike(like))
        query = query.filter(or_(*conds))
        interpreted["query"] = q
    if category:
        query = query.join(Category, Product.category_id == Category.id).filter(
            or_(Category.name.ilike(f"%{category}%"), Category.slug.ilike(f"%{category}%"))
        )
        interpreted["category"] = category
    if material:
        query = query.filter(Product.material.ilike(f"%{material}%"))
        interpreted["material"] = material
    if state:
        query = query.join(ArtisanProfile, Product.artisan_id == ArtisanProfile.id).filter(
            ArtisanProfile.state.ilike(f"%{state}%")
        )
        interpreted["state"] = state
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if customizable:
        query = query.filter(Product.customization_available.is_(True))
        interpreted["customizable"] = True
    if bulk_available:
        query = query.filter(Product.bulk_moq.isnot(None))
        interpreted["bulk_available"] = True
    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "popular":
        query = query.order_by(Product.view_count.desc())
    else:
        query = query.order_by(Product.published_at.desc().nullslast(), Product.created_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [product_public(p, include_attributes=False) for p in rows],
        "total": total, "page": page, "page_size": page_size,
        "interpreted": interpreted or None,
    }


@router.get("/{product_id}", summary="Product detail (public) — artisan-centric")
def get_product(product_id: str, request: Request, db: Session = Depends(get_db),
                user: Optional[User] = Depends(get_optional_user)):
    product = product_service.get_product(db, product_id)
    if product.lifecycle != ProductLifecycle.PUBLISHED and (user is None or user.role != "ADMIN"):
        from app.core.errors import NotFoundError

        raise NotFoundError("This product is not available.")
    analytics_service.increment_view(db, product, user)
    data = product_public(product)
    profile = db.query(ArtisanProfile).filter(ArtisanProfile.id == product.artisan_id).first()
    if profile:
        from app.api.v1.artisans import public_artisan

        data["artisan"] = public_artisan(db, profile)
    from app.models.engagement import Review

    reviews = (
        db.query(Review).filter(Review.product_id == product.id).order_by(Review.created_at.desc()).limit(10).all()
    )
    data["reviews"] = [
        {
            "rating": r.product_rating, "text": r.text, "verified": r.is_verified_purchase,
            "buyer_name": _buyer_display_name(db, r.buyer_id), "created_at": r.created_at.isoformat(),
        }
        for r in reviews
    ]
    more = (
        db.query(Product)
        .filter(Product.artisan_id == product.artisan_id, Product.id != product.id,
                Product.lifecycle == ProductLifecycle.PUBLISHED, Product.deleted_at.is_(None))
        .limit(4).all()
    )
    data["more_from_artisan"] = [product_public(p, include_attributes=False) for p in more]
    return data


def _buyer_display_name(db: Session, buyer_id: str) -> str:
    user = db.query(User).filter(User.id == buyer_id).first()
    if user is None:
        return "Buyer"
    name = user.full_name or "Buyer"
    parts = name.split()
    return parts[0] + (" " + parts[-1][0] + "." if len(parts) > 1 else "")


@router.patch("/{product_id}", summary="Update my product")
def update_product(product_id: str, payload: ProductUpdateIn,
                   user: User = Depends(require_roles("ARTISAN", "ADMIN")), db: Session = Depends(get_db)):
    product = product_service.get_owned_product(db, product_id, user)
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    product_service.update_product(db, product, changes)
    return {"id": product.id, "lifecycle": product.lifecycle, "updated": True}


@router.post("/{product_id}/publish", summary="Publish after review")
def publish(product_id: str, user: User = Depends(require_roles("ARTISAN", "ADMIN")),
            db: Session = Depends(get_db)):
    product = product_service.get_owned_product(db, product_id, user)
    product_service.publish(db, product)
    from app.core.events import bus, PRODUCT_PUBLISHED

    bus.publish(PRODUCT_PUBLISHED, {"product_id": product.id})
    analytics_service.track(db, event_type="PRODUCT_PUBLISHED", actor=user, entity_type="product", entity_id=product.id)
    return {"id": product.id, "lifecycle": product.lifecycle}


@router.delete("/{product_id}", summary="Archive my product")
def delete_product(product_id: str, user: User = Depends(require_roles("ARTISAN", "ADMIN")),
                   db: Session = Depends(get_db)):
    product = product_service.get_owned_product(db, product_id, user)
    product_service.soft_delete(db, product)
    return {"archived": True}


@router.post("/{product_id}/images", summary="Upload a product photo")
def upload_image(product_id: str, file: UploadFile = File(...),
                 user: User = Depends(require_roles("ARTISAN", "ADMIN")), db: Session = Depends(get_db)):
    enforce("ai", user.id)  # image processing shares AI limits
    product = product_service.get_owned_product(db, product_id, user)
    data = file.file.read()
    stored = store_upload(data, prefix="product")
    quality = None
    try:
        from app.ai.providers import get_vision

        result = get_vision().analyze_quality(data)
        quality = result.score
    except Exception:
        quality = None
    img = product_service.add_image(
        db, product, url=stored["url"], mime=stored["mime"], size=stored["size"],
        quality_score=quality, width=None, height=None,
    )
    return {
        "image_id": img.id, "url": img.original_url, "is_primary": img.is_primary,
        "quality_score": quality,
    }
