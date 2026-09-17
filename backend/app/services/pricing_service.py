"""Smart Pricing Assistant (blueprint §18, §19).

Decision support, never a mandate: cost model + market signals + demand →
recommendation with a plain-language explanation and full transparency of
contributions. The artisan can Accept / Edit / Ignore.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.commerce import OrderItem, Order
from app.models.product import Product
from app.models.profile import ArtisanProfile

# Market reference bands (demo reference data — production: per-category stats)
MARKET_BANDS: dict[str, tuple[float, float, float]] = {
    # key: (low, high, typical_markup_over_cost)
    "saree": (1050, 1400, 1.55),
    "basket": (380, 650, 1.6),
    "pottery": (300, 700, 1.65),
    "default": (1.5, 2.2, 1.5),  # multipliers when no band matches
}


@dataclass
class PricingInputs:
    material_cost: float = 0.0
    labour_cost: float = 0.0
    packaging_cost: float = 0.0
    shipping_estimate: float = 0.0
    overhead: float = 0.0
    desired_margin_pct: float = 30.0
    production_days: Optional[int] = None
    category_hint: Optional[str] = None
    product_id: Optional[str] = None

    @property
    def total_cost(self) -> float:
        return self.material_cost + self.labour_cost + self.packaging_cost + self.shipping_estimate + self.overhead


@dataclass
class PriceRecommendation:
    estimated_cost: float
    market_low: float
    market_high: float
    suggested_price: float
    estimated_margin: float
    margin_pct: float
    demand_signal: str
    explanation: str
    contributions: dict = field(default_factory=dict)


class PricingService:
    def recommend(self, db: Session, *, user: User, inputs: PricingInputs) -> PriceRecommendation:
        cost = inputs.total_cost
        band = self._market_band(inputs.category_hint)
        demand = self._demand_signal(db, inputs.product_id)

        if band is not None:
            # absolute market band matched a known category
            market_low, market_high, _typical = band
            suggested = (market_low + market_high) / 2
            # Never suggest below a safe margin over cost.
            suggested = max(suggested, cost * 1.15)
        else:
            multiplier_path = MARKET_BANDS["default"]
            market_low = cost * multiplier_path[0]
            market_high = cost * multiplier_path[1]
            suggested = cost * multiplier_path[2] * (1 + max(0.0, inputs.desired_margin_pct - 30) / 100)

        margin = suggested - cost
        from app.ai.providers import get_llm

        explanation = get_llm().explain_price(
            {
                "total_cost": cost,
                "material_cost": inputs.material_cost,
                "labour_cost": inputs.labour_cost,
            },
            suggested,
            market_low,
            market_high,
        )
        return PriceRecommendation(
            estimated_cost=round(cost, 2),
            market_low=round(market_low, 2),
            market_high=round(market_high, 2),
            suggested_price=round(suggested, 2),
            estimated_margin=round(margin, 2),
            margin_pct=round((margin / suggested) * 100, 1) if suggested else 0,
            demand_signal=demand,
            explanation=explanation,
            contributions={
                "materials": inputs.material_cost,
                "labour": inputs.labour_cost,
                "packaging": inputs.packaging_cost,
                "shipping": inputs.shipping_estimate,
                "overhead": inputs.overhead,
                "margin": round(margin, 2),
            },
        )

    def _market_band(self, category_hint: Optional[str]) -> Optional[tuple[float, float, float]]:
        """Returns an absolute (low, high, typical) band only for known categories;
        None means use the multiplier path."""
        if not category_hint:
            return None
        key = str(category_hint).lower()
        for name in ("saree", "basket", "pottery"):
            if name in key:
                return MARKET_BANDS[name]
        return None

    def _demand_signal(self, db: Session, product_id: Optional[str]) -> str:
        if not product_id:
            return "New product — no demand data yet"
        from app.models.product import Product as P

        product = db.query(P).filter(P.id == product_id).first()
        if product is None:
            return "No demand data yet"
        views = product.view_count
        if views >= 100:
            return "High"
        if views >= 20:
            return "Medium"
        return "Low"


pricing_service = PricingService()
