"""User preference settings: easy mode, voice, font scale, region.

Kept in a dedicated table so `create_all` adds it without migrating the
existing `users` table (SQLite dev DB + Postgres prod share this contract).
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin, UUIDPkMixin


class UserSettings(UUIDPkMixin, TimestampMixin, Base):
    """One row per user. All fields optional; missing row == defaults."""

    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    preferred_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    preferred_voice_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    voice_enabled: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    easy_mode_enabled: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    font_scale: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 1.0 | 1.25 | 1.5
    region: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    __table_args__ = (UniqueConstraint("user_id", name="uq_user_settings_user"),)
