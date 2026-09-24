"""SQLAlchemy models. UUID primary keys (CHAR(36)), timestamps, soft deletes.

All model modules are imported here so `Base.metadata.create_all()` sees them.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base  # re-export for model modules

__all__ = ["Base"]


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDPkMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


import app.models.sih  # noqa: E402,F401  SIH evidence models register with Base (must come after mixins)
import app.models.settings  # noqa: E402,F401  user accessibility/voice/language preferences
import app.models.whatsapp  # noqa: E402,F401  WhatsApp conversation sessions
