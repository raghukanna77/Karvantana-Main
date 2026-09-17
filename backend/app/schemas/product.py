"""Product / commerce schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ProductCreateIn(BaseModel):
    title: str = Field(default="", max_length=250)
    category: Optional[str] = None
    material: Optional[str] = Field(default=None, max_length=200)
    technique: Optional[str] = Field(default=None, max_length=120)
    colour: Optional[str] = Field(default=None, max_length=60)
    origin: Optional[str] = Field(default=None, max_length=120)
    usage: Optional[str] = Field(default=None, max_length=300)
    dimensions: Optional[str] = Field(default=None, max_length=120)
    production_days: Optional[int] = Field(default=None, ge=0, le=365)
    price: Optional[float] = Field(default=None, ge=0)
    inventory_mode: str = Field(default="STOCK", pattern="^(STOCK|MADE_TO_ORDER|PRE_ORDER|CUSTOM)$")
    stock_quantity: int = Field(default=0, ge=0)
    moq: int = Field(default=1, ge=1)
    bulk_moq: Optional[int] = Field(default=None, ge=2)
    bulk_price: Optional[float] = Field(default=None, ge=0)
    customization_available: bool = False


class ProductUpdateIn(BaseModel):
    title: Optional[str] = Field(default=None, max_length=250)
    short_description: Optional[str] = Field(default=None, max_length=400)
    description: Optional[str] = None
    craft_story: Optional[str] = None
    material: Optional[str] = Field(default=None, max_length=200)
    technique: Optional[str] = Field(default=None, max_length=120)
    colour: Optional[str] = Field(default=None, max_length=60)
    origin: Optional[str] = Field(default=None, max_length=120)
    usage: Optional[str] = Field(default=None, max_length=300)
    dimensions: Optional[str] = Field(default=None, max_length=120)
    production_days: Optional[int] = Field(default=None, ge=0, le=365)
    price: Optional[float] = Field(default=None, ge=0)
    inventory_mode: Optional[str] = Field(default=None, pattern="^(STOCK|MADE_TO_ORDER|PRE_ORDER|CUSTOM)$")
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    moq: Optional[int] = Field(default=None, ge=1)
    bulk_moq: Optional[int] = Field(default=None, ge=2)
    bulk_price: Optional[float] = Field(default=None, ge=0)
    customization_available: Optional[bool] = None
    keywords: Optional[str] = Field(default=None, max_length=500)


class VoiceIn(BaseModel):
    text: Optional[str] = Field(default=None, max_length=4000, description="Client-captured transcript (browser SpeechRecognition)")
    language_hint: Optional[str] = Field(default=None, max_length=10)


class CatalogueGenerateIn(BaseModel):
    product_id: str
    transcript_en: str = Field(min_length=2, max_length=4000)
    transcript_original: str = Field(default="", max_length=4000)


class RegenerateFieldIn(BaseModel):
    field: str = Field(pattern="^(title|short_description|description|keywords|highlights)$")


class PricingInputsIn(BaseModel):
    material_cost: float = Field(ge=0)
    labour_cost: float = Field(ge=0)
    packaging_cost: float = 0
    shipping_estimate: float = 0
    overhead: float = 0
    desired_margin_pct: float = Field(default=30, ge=0, le=90)
    production_days: Optional[int] = None
    category_hint: Optional[str] = None
    product_id: Optional[str] = None


class OrderCreateIn(BaseModel):
    items: list[dict] = Field(min_length=1)
    shipping_address: dict
    buyer_note: Optional[str] = Field(default=None, max_length=1000)


class OrderStatusIn(BaseModel):
    status: str
    note: Optional[str] = Field(default=None, max_length=300)


class ReviewIn(BaseModel):
    order_item_id: str
    product_rating: int = Field(ge=1, le=5)
    text: Optional[str] = Field(default=None, max_length=2000)
    quality_rating: Optional[int] = Field(default=None, ge=1, le=5)
    communication_rating: Optional[int] = Field(default=None, ge=1, le=5)
    value_rating: Optional[int] = Field(default=None, ge=1, le=5)
    delivery_rating: Optional[int] = Field(default=None, ge=1, le=5)


class BulkRequestIn(BaseModel):
    title: str = Field(min_length=4, max_length=200)
    description: str = Field(default="", max_length=2000)
    quantity: int = Field(ge=2)
    max_unit_price: Optional[float] = Field(default=None, ge=0)
    required_by: Optional[str] = None
    customization_required: bool = False
    category_hint: Optional[str] = Field(default=None, max_length=100)


class QuoteIn(BaseModel):
    request_type: str = Field(pattern="^(BULK|CUSTOM)$")
    request_id: str
    unit_price: float = Field(gt=0)
    lead_time_days: int = Field(ge=1, le=180)
    note: Optional[str] = Field(default=None, max_length=1000)
    quantity: Optional[int] = Field(default=None, ge=1)


class AcceptQuoteIn(BaseModel):
    shipping_address: dict


class CustomRequestIn(BaseModel):
    artisan_id: str
    title: str = Field(min_length=4, max_length=200)
    description: str = Field(default="", max_length=2000)
    quantity: int = Field(default=1, ge=1, le=500)
    budget: Optional[float] = Field(default=None, ge=0)
    required_by: Optional[str] = None
    product_id: Optional[str] = None
