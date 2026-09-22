"""Auth endpoints (/api/v1/auth)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AuthenticationError
from app.models.settings import UserSettings
from app.schemas.auth import (
    LoginIn, LogoutIn, OTPRequestIn, OTPVerifyIn, RefreshIn, RegisterIn, TokenPairOut, UserSettingsIn,
)
from app.security.dependencies import get_current_user
from app.security.rate_limit import enforce
from app.services.auth_service import auth_service
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/otp/request", summary="Request a mobile OTP code")
def request_otp(payload: OTPRequestIn, request: Request, db: Session = Depends(get_db)):
    enforce("auth", request.client.host if request.client else "anonymous")
    return auth_service.request_otp(db, payload.phone)


@router.post("/otp/verify", response_model=TokenPairOut, summary="Verify OTP (signs in or creates account)")
def verify_otp(payload: OTPVerifyIn, request: Request, db: Session = Depends(get_db)):
    enforce("auth", request.client.host if request.client else "anonymous")
    return auth_service.verify_otp(db, payload.phone, payload.code, payload.full_name)


@router.post("/register", response_model=TokenPairOut, summary="Create an account with email + password")
def register(payload: RegisterIn, request: Request, db: Session = Depends(get_db)):
    enforce("auth", request.client.host if request.client else "anonymous")
    return auth_service.register(db, full_name=payload.full_name, email=payload.email,
                                 password=payload.password, role=payload.role)


@router.post("/login", response_model=TokenPairOut, summary="Sign in with email + password")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    enforce("auth", request.client.host if request.client else "anonymous")
    return auth_service.login(db, email=payload.email, password=payload.password)


@router.post("/refresh", response_model=TokenPairOut, summary="Rotate refresh token")
def refresh(payload: RefreshIn, db: Session = Depends(get_db)):
    return auth_service.refresh(db, payload.refresh_token)


@router.post("/logout", summary="Revoke the refresh token")
def logout(payload: LogoutIn, db: Session = Depends(get_db)):
    auth_service.logout(db, payload.refresh_token)
    return {"success": True}


@router.get("/me", summary="Current user profile")
def me(user: User = Depends(get_current_user)):
    return auth_service.public_user(user)


@router.patch("/me", summary="Update my profile (language, voice, accessibility, region)")
def update_me(payload: UserSettingsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # users.preferred_language stays the canonical mirror of the UI language.
    if payload.preferred_language is not None:
        user.preferred_language = payload.preferred_language
    # Settings live in user_settings (one row per user, upserted).
    row = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    if row is None:
        row = UserSettings(user_id=user.id)
        db.add(row)
    for field in ("preferred_language", "preferred_voice_language", "voice_enabled",
                  "easy_mode_enabled", "font_scale", "region", "district", "state"):
        value = getattr(payload, field)
        if value is not None:
            setattr(row, field, value)
    db.add(row)
    db.commit()
    out = auth_service.public_user(user)
    out["settings"] = {
        "preferred_language": row.preferred_language or user.preferred_language,
        "preferred_voice_language": row.preferred_voice_language,
        "voice_enabled": row.voice_enabled if row.voice_enabled is not None else True,
        "easy_mode_enabled": bool(row.easy_mode_enabled),
        "font_scale": row.font_scale or 1.0,
        "region": row.region, "district": row.district, "state": row.state,
    }
    return out
