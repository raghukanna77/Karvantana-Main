"""Taxonomy reference data: categories, craft types, materials, languages."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin, UUIDPkMixin


class Category(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    parent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("categories.id"), nullable=True)


class CraftType(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "craft_types"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class Material(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "materials"

    name: Mapped[str] = mapped_column(String(100), unique=True)


class Language(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(60))
