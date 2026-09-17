"""Unit tests: pricing model."""

from __future__ import annotations

from app.services.pricing_service import PricingInputs, PricingService


def test_total_cost_sums_all_components():
    inputs = PricingInputs(material_cost=400, labour_cost=350, packaging_cost=30, shipping_estimate=50, overhead=20)
    assert inputs.total_cost == 850


def test_recommendation_respects_market_band_and_explains():
    svc = PricingService()
    rec = svc.recommend(None, user=None, inputs=PricingInputs(material_cost=420, labour_cost=380, packaging_cost=40, shipping_estimate=60, category_hint="saree"))
    # saree band midpoint 1225, never below cost*1.15
    assert rec.suggested_price >= 1225
    assert rec.market_low == 1050 and rec.market_high == 1400
    assert "₹" in rec.explanation
    assert rec.estimated_margin > 0


def test_recommendation_never_below_cost_for_unknown_category():
    svc = PricingService()
    rec = svc.recommend(None, user=None, inputs=PricingInputs(material_cost=1000, labour_cost=900, category_hint="exotic-wood"))
    assert rec.suggested_price >= (1900 * 1.5) * 0.99  # default multiplier path
    assert rec.margin_pct > 0
