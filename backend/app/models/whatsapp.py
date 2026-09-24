"""WhatsApp conversational onboarding: per-phone session state.

The WhatsApp channel is a *front-end* over the same listing pipeline the main
app drives (blueprint §43 "many front doors, one pipeline"). All AI results live
in the standard Product/AIGeneration tables; this table only remembers where an
interrupted conversation should resume.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin, UUIDPkMixin, utcnow


class WhatsAppMessage(UUIDPkMixin, Base):
    """Persisted chat transcript per phone number (both directions).

    In the prototype the simulator reads this table to render the thread;
    it stands in for WhatsApp's own message history, which a real Cloud API
    integration would query/receive instead.
    """

    __tablename__ = "whatsapp_messages"

    phone: Mapped[str] = mapped_column(String(20), index=True)
    direction: Mapped[str] = mapped_column(String(3))  # "IN" | "OUT"
    message_id: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(20))  # text|image|voice|interactive
    payload: Mapped[dict] = mapped_column(__import__("sqlalchemy").JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class WhatsAppState:
    # one state per message exchange (feature spec steps 1–6)
    AWAITING_PHOTO = "AWAITING_PHOTO"
    AWAITING_VOICE = "AWAITING_VOICE"
    PROCESSING = "PROCESSING"
    REVIEW = "REVIEW"
    EDITING = "EDITING"  # sub-state of REVIEW: bot asked "what would you like to change?"
    IDLE = "IDLE"

    ALL = (AWAITING_PHOTO, AWAITING_VOICE, PROCESSING, REVIEW, EDITING, IDLE)


class WhatsAppSession(UUIDPkMixin, TimestampMixin, Base):
    """Conversation state per artisan phone number (resumable if interrupted)."""

    __tablename__ = "whatsapp_sessions"
    __table_args__ = (UniqueConstraint("phone", name="uq_whatsapp_session_phone"),)

    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    current_state: Mapped[str] = mapped_column(String(20), default=WhatsAppState.AWAITING_PHOTO, index=True)
    draft_listing_id: Mapped[Optional[str]] = mapped_column(ForeignKey("products.id"), nullable=True)
    # Last transcript used for catalogue generation — edit corrections are
    # appended to this and the listing is genuinely regenerated (not redisplayed).
    last_transcript_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_transcript_original: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_price: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    published_product_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    last_message_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, index=True)
