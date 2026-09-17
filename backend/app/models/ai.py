"""AI models: generations (audit trail), voice transcripts, usage tracking.

Every AI action stores input, provider, model, prompt version, output,
confidence and human approval for explainability (blueprint §76).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin, UUIDPkMixin, utcnow


class AIGeneration(UUIDPkMixin, TimestampMixin, Base):
    """One AI inference event, fully auditable."""

    __tablename__ = "ai_generations"
    __table_args__ = (Index("ix_ai_gen_user_created", "user_id", "created_at"),)

    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    product_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    task: Mapped[str] = mapped_column(String(60), index=True)  # catalogue|pricing|transcription|translation|image_enhance|assistant|requirement_parse
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(80))
    prompt_version: Mapped[str] = mapped_column(String(60), default="v1")
    input_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # truncated inputs only
    output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS")  # SUCCESS|FAILED
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # user id on approval
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    corrected: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # artisan edits for quality loop


class VoiceTranscript(UUIDPkMixin, Base):
    """Original + translated transcript; never overwritten."""

    __tablename__ = "voice_transcripts"

    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    product_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    original_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    translated_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AIUsage(UUIDPkMixin, Base):
    """Per-request usage for cost tracking and admin monitoring (blueprint §81)."""

    __tablename__ = "ai_usage"

    task: Mapped[str] = mapped_column(String(60), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(80))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(default=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
