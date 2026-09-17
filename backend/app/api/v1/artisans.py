"""Artisan endpoints (/api/v1/artisans)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import NotFoundError, ValidationFailedError
from app.models.engagement import ArtisanReputation, Follow, SavedArtisan
from app.models.product import Product
from app.models.profile import ArtisanProfile, Cluster, ClusterMember
from app.models.user import User
from app.schemas.product import ProductCreateIn, ProductUpdateIn
from app.security.dependencies import get_current_user, get_optional_user, require_roles
from app.services.product_service import product_service

router = APIRouter(prefix="/artisans", tags=["artisans"])


def _profile(db: Session, user: User) -> ArtisanProfile:
    profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
    if profile is None:
        raise NotFoundError("Complete artisan onboarding first.")
    return profile


def public_artisan(db: Session, profile: ArtisanProfile, viewer: Optional[User] = None) -> dict:
    rep = db.query(ArtisanReputation).filter(ArtisanReputation.artisan_id == profile.id).first()
    products = (
        db.query(Product)
        .filter(Product.artisan_id == profile.id, Product.lifecycle == "PUBLISHED", Product.deleted_at.is_(None))
        .count()
    )
    following = False
    if viewer is not None:
        following = db.query(Follow).filter(Follow.user_id == viewer.id, Follow.artisan_id == profile.id).first() is not None
    return {
        "id": profile.id,
        "display_name": profile.display_name,
        "craft": profile.craft_specialization,
        "story": profile.craft_story,
        "location": ", ".join(filter(None, [profile.village, profile.district, profile.state])),
        "years_of_experience": profile.years_of_experience,
        "organization_type": profile.organization_type,
        "verification_level": profile.verification_level,
        "languages": profile.languages.split(",") if profile.languages else [],
        "customization": True,  # refined per-product below in listings
        "stats": {
            "published_products": products,
            "rating": rep.rating_avg if rep else None,
            "rating_count": rep.rating_count if rep else 0,
            "verified_orders": rep.verified_orders if rep else 0,
            "repeat_buyers": rep.repeat_buyers if rep else 0,
            "response_rate": rep.response_rate if rep else 1.0,
            "on_time_rate": rep.on_time_fulfilment_rate if rep else 1.0,
            "following": following,
        },
    }


@router.get("", summary="Browse artisans (public)")
def list_artisans(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(default=None, max_length=100),
    state: Optional[str] = Query(default=None, max_length=120),
    craft: Optional[str] = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
):
    query = db.query(ArtisanProfile).filter(ArtisanProfile.onboarding_complete.is_(True))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(ArtisanProfile.display_name.ilike(like),
                                 ArtisanProfile.craft_specialization.ilike(like)))
    if state:
        query = query.filter(ArtisanProfile.state.ilike(f"%{state}%"))
    if craft:
        query = query.filter(ArtisanProfile.craft_specialization.ilike(f"%{craft}%"))
    total = query.count()
    rows = query.order_by(ArtisanProfile.display_name).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [public_artisan(db, p) for p in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/me", summary="My artisan profile", dependencies=[Depends(require_roles("ARTISAN", "ADMIN"))])
def my_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return public_artisan(db, _profile(db, user))


@router.patch("/me", summary="Update my artisan profile", dependencies=[Depends(require_roles("ARTISAN", "ADMIN"))])
def update_profile(payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = _profile(db, user)
    allowed = {
        "display_name", "craft_specialization", "craft_story", "village", "city", "district",
        "state", "years_of_experience", "organization_type", "organization_name",
        "production_capacity", "min_bulk_quantity", "gst_registered", "payment_ready",
        "languages",
    }
    onboarding_fields = {
        "display_name", "craft_specialization", "state", "district", "village",
        "years_of_experience", "organization_type", "production_capacity", "min_bulk_quantity",
    }
    touched_onboarding = False
    for key, value in (payload or {}).items():
        if key in allowed:
            if key == "languages" and isinstance(value, list):
                value = ",".join(value)
            setattr(profile, key, value)
            if key in onboarding_fields and value not in (None, ""):
                touched_onboarding = True
    if touched_onboarding:
        profile.onboarding_step = max(profile.onboarding_step, 2)
        if profile.display_name and profile.state:
            profile.onboarding_complete = True
    db.flush()
    return public_artisan(db, profile)


@router.post("/me/onboarding", summary="Progressive onboarding: upserts the artisan profile")
def onboarding(payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
    if profile is None:
        profile = ArtisanProfile(user_id=user.id, display_name=user.full_name)
        db.add(profile)
        db.flush()
    step = int(payload.get("step", 1))
    data = payload.get("data", {}) or {}
    allowed = {
        "display_name", "craft_specialization", "craft_story", "village", "city", "district",
        "state", "years_of_experience", "organization_type", "organization_name",
        "production_capacity", "min_bulk_quantity", "gst_registered", "payment_ready", "languages",
    }
    for key, value in data.items():
        if key in allowed:
            if key == "languages" and isinstance(value, list):
                value = ",".join(value)
            setattr(profile, key, value)
    profile.onboarding_step = max(profile.onboarding_step, step)
    if step >= 3 and profile.display_name and profile.state:
        profile.onboarding_complete = True
    db.flush()
    return {"onboarding_step": profile.onboarding_step, "onboarding_complete": profile.onboarding_complete}


@router.get("/{artisan_id}", summary="Public artisan profile")
def get_artisan(artisan_id: str, db: Session = Depends(get_db), viewer: Optional[User] = Depends(get_optional_user)):
    profile = db.query(ArtisanProfile).filter(ArtisanProfile.id == artisan_id).first()
    if profile is None:
        raise NotFoundError("Artisan not found.")
    data = public_artisan(db, profile, viewer)
    products = (
        db.query(Product)
        .filter(Product.artisan_id == artisan_id, Product.lifecycle == "PUBLISHED", Product.deleted_at.is_(None))
        .order_by(Product.updated_at.desc())
        .all()
    )
    from app.api.v1.products import product_public

    data["products"] = [product_public(p) for p in products]
    return data


@router.post("/{artisan_id}/follow", summary="Follow an artisan", dependencies=[Depends(require_roles("BUYER", "B2B_BUYER", "ARTISAN", "ADMIN"))])
def follow(artisan_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(ArtisanProfile).filter(ArtisanProfile.id == artisan_id).first()
    if profile is None:
        raise NotFoundError("Artisan not found.")
    if profile.user_id == user.id:
        raise ValidationFailedError("You can't follow your own studio.")
    existing = db.query(Follow).filter(Follow.user_id == user.id, Follow.artisan_id == artisan_id).first()
    if existing is None:
        db.add(Follow(user_id=user.id, artisan_id=artisan_id))
        from app.core.events import bus, ARTISAN_FOLLOWED

        bus.publish(ARTISAN_FOLLOWED, {"artisan_id": artisan_id, "user_id": user.id})
        db.flush()
    return {"following": True}


@router.delete("/{artisan_id}/follow", summary="Unfollow an artisan")
def unfollow(artisan_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Follow).filter(Follow.user_id == user.id, Follow.artisan_id == artisan_id).delete()
    return {"following": False}


@router.post("/{artisan_id}/save", summary="Save an artisan", dependencies=[Depends(require_roles("BUYER", "B2B_BUYER", "ADMIN"))])
def save_artisan(artisan_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.query(ArtisanProfile).filter(ArtisanProfile.id == artisan_id).first() is None:
        raise NotFoundError("Artisan not found.")
    if not db.query(SavedArtisan).filter(SavedArtisan.user_id == user.id, SavedArtisan.artisan_id == artisan_id).first():
        db.add(SavedArtisan(user_id=user.id, artisan_id=artisan_id))
        db.flush()
    return {"saved": True}


@router.get("/saved/list", summary="My saved artisans", dependencies=[Depends(require_roles("BUYER", "B2B_BUYER", "ADMIN"))])
def saved_artisans(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(SavedArtisan, ArtisanProfile)
        .join(ArtisanProfile, SavedArtisan.artisan_id == ArtisanProfile.id)
        .filter(SavedArtisan.user_id == user.id)
        .all()
    )
    return {"items": [public_artisan(db, p) for _, p in rows]}
