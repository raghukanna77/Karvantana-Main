"""Analytics, demand intelligence and audit models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin, UUIDPkMixin, utcnow


class AnalyticsEvent(UUIDPkMixin, Base):
    """Raw behavioral events feeding demand intelligence and KPIs (blueprint §102)."""

    __tablename__ = "analytics_events"
    __table_args__ = (
        Index("ix_ae_type_created", "event_type", "created_at"),
        Index("ix_ae_entity", "entity_type", "entity_id"),
    )

    event_type: Mapped[str] = mapped_column(String(40), index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class DemandSignal(UUIDPkMixin, Base):
    """Materialized demand aggregates per product/category/region (blueprint §33)."""

    __tablename__ = "demand_signals"
    __table_args__ = (Index("ix_demand_scope", "scope", "scope_id"),)

    scope: Mapped[str] = mapped_column(String(20))  # PRODUCT | CATEGORY | CRAFT
    scope_id: Mapped[str] = mapped_column(String(36))
    period: Mapped[str] = mapped_column(String(20), default="WEEKLY")
    views: Mapped[int] = mapped_column(Integer, default=0)
    searches: Mapped[int] = mapped_column(Integer, default=0)
    enquiries: Mapped[int] = mapped_column(Integer, default=0)
    orders: Mapped[int] = mapped_column(Integer, default=0)
    trend: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # HIGH|MEDIUM|LOW|RISING|FALLING
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(UUIDPkMixin, Base):
    """Immutable audit trail for security-relevant and governance actions."""

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_created", "created_at"),)

    actor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    detail: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

