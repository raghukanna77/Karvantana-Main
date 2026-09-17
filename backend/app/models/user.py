"""Identity models: users, OTP codes, refresh tokens, consents."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin, UUIDPkMixin, new_uuid, utcnow


class User(UUIDPkMixin, TimestampMixin, Base):
    """Platform user. Role is server-controlled; never settable by clients."""

    __tablename__ = "users"

    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(200))
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), index=True)  # Role enum value
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)  # seeded demo account
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class OTPCode(UUIDPkMixin, Base):
    """Mobile OTP for passwordless sign-in. Codes are hashed; demo mode returns them to the client."""

    __tablename__ = "otp_codes"

    phone: Mapped[str] = mapped_column(String(20), index=True)
    code_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class RefreshToken(UUIDPkMixin, Base):
    """Rotating refresh tokens; revocation via revoked_at."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Consent(UUIDPkMixin, Base):
    """Explicit user consents (location capture, data processing, marketing)."""

    __tablename__ = "consents"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    consent_type: Mapped[str] = mapped_column(String(50), index=True)  # location | ai_processing | ...
    granted: Mapped[bool] = mapped_column(Boolean, default=False)
    granted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (UniqueConstraint("user_id", "consent_type", name="uq_consent_user_type"),)
