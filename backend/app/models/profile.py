"""Profile models: artisan profiles, buyer profiles, business (B2B) profiles, clusters."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, UUIDPkMixin


class ArtisanProfile(UUIDPkMixin, TimestampMixin, Base):
    """The artisan business identity. `user_id` links to the login account."""

    __tablename__ = "artisan_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    craft_specialization: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    craft_story: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    village: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    years_of_experience: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    organization_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)  # INDIVIDUAL|SHG|COOPERATIVE|NGO
    organization_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    production_capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # units/month
    min_bulk_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gst_registered: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    payment_ready: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    onboarding_step: Mapped[int] = mapped_column(Integer, default=0)  # progressive onboarding
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_level: Mapped[str] = mapped_column(String(30), default="BASIC_PROFILE")  # BASIC_PROFILE|VERIFIED_ARTISAN|VERIFIED_ORGANIZATION|TRUSTED_SELLER
    verification_status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING|VERIFIED|REJECTED|SUSPENDED
    languages: Mapped[str] = mapped_column(String(300), default="en")  # comma-separated codes
    response_rate: Mapped[float] = mapped_column(Float, default=1.0)
    avatar_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    user: Mapped["User"] = relationship("User", lazy="joined")  # noqa: F821


class BuyerProfile(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "buyer_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)


class BusinessProfile(UUIDPkMixin, TimestampMixin, Base):
    """B2B / institutional buyer organization profile."""

    __tablename__ = "business_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    business_name: Mapped[str] = mapped_column(String(200))
    buyer_type: Mapped[str] = mapped_column(String(30), default="RETAILER")  # RETAILER|BOUTIQUE|HOTEL|CORPORATE_GIFTING|EXPORTER|WHOLESALER|GOVERNMENT|NGO|EDUCATION
    gst_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Cluster(UUIDPkMixin, TimestampMixin, Base):
    """Artisan cluster / producer group managed by a cluster manager."""

    __tablename__ = "clusters"

    name: Mapped[str] = mapped_column(String(200))
    region: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manager_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)


class ClusterMember(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "cluster_members"

    cluster_id: Mapped[str] = mapped_column(ForeignKey("clusters.id"), index=True)
    artisan_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)  # artisan user id

    __table_args__ = (UniqueConstraint("cluster_id", "artisan_id", name="uq_cluster_member"),)
