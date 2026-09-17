"""Demo LLM provider.

Deterministic, rule/heuristic-based implementations of the LLMProvider
interface so catalogue generation, requirement parsing and the business
assistant work end-to-end without external APIs. Every function is honest:
it composes output ONLY from structured inputs (extraction/translation
results) and says so when data is missing. Real vendors (OpenAI etc.)
implement the same interface via settings.AI_PROVIDER.
"""

from __future__ import annotations

from typing import Optional

CRAFT_TEMPLATES = {
    "saree": {
        "highlights": ["Handwoven on traditional loom", "Natural dyes", "Artisan-direct", "Custom orders available"],
        "care": "Dry clean or gentle hand wash in cold water. Dry in shade.",
    },
    "basket": {
        "highlights": ["Handwoven bamboo", "Eco-friendly natural material", "Sturdy everyday use", "Custom sizes available"],
        "care": "Wipe with a dry cloth. Keep away from prolonged moisture.",
    },
    "pottery": {
        "highlights": ["Hand-thrown terracotta", "Traditional kiln firing", "Food-safe glaze options", "Custom orders available"],
        "care": "Hand wash. Avoid dishwasher and microwave.",
    },
    "default": {
        "highlights": ["Handcrafted by artisan", "Traditional technique", "Natural materials", "Custom orders available"],
        "care": "Spot clean. Handle with care.",
    },
}


class DemoLLMProvider:
    name = "demo-llm"
    model = "karvantana-rules-v1"

    # ---------------------------------------------------------------- catalogue

    def generate_catalogue(self, extracted: dict, artisan_name: str, region: str) -> dict:
        """Compose catalogue copy from structured extraction output only."""
        kind = _classify_kind(extracted)
        material = extracted.get("material") or "natural materials"
        technique = extracted.get("technique") or "traditional craft technique"
        usage = extracted.get("usage") or "everyday use and gifting"
        prod_days = extracted.get("production_days")
        title = f"Handwoven {material.title()} {kind.title()}" if kind else f"Handcrafted {material.title()} Piece"

        short_desc = (
            f"A {technique.lower()} {kind or 'piece'} in {material}, handcrafted by {artisan_name}"
            + (f" of {region}" if region else "")
            + f". Ideal for {usage}."
        )

        full_desc_lines = [
            f"Bring home a piece made slowly and skillfully by {artisan_name}"
            + (f", an artisan from {region}" if region else ".") + ".",
            f"Each {kind or 'piece'} is worked in {material} using {technique.lower()}, so small variations are the signature of a handmade product — no two are exactly alike.",
            f"Perfect for {usage}.",
        ]
        if prod_days:
            full_desc_lines.append(f"Made to order in about {prod_days} day(s), exactly as practiced in this workshop.")
        tpl = CRAFT_TEMPLATES.get(kind, CRAFT_TEMPLATES["default"])
        full_desc_lines.append(f"Care: {tpl['care']}")

        keywords = _keywords_for(kind, material, technique, region)

        return {
            "title": title,
            "short_description": short_desc,
            "description": "\n\n".join(full_desc_lines),
            "highlights": tpl["highlights"],
            "keywords": keywords,
        }

    # ------------------------------------------------------- requirement parsing

    def parse_buyer_requirement(self, text: str) -> dict:
        """Structured parse of buyer natural language → requirement fields."""
        import re

        qty = None
        m = re.search(r"(\d[\d,]*)\s*(pieces|pcs|units|nos|items|baskets|boxes|bags|sarees)?", text.lower())
        if m:
            qty = int(m.group(1).replace(",", ""))
        budget = None
        m = re.search(r"(?:under|below|upto|up to|budget of|₹|rs\.?|inr)\s*(?:₹|rs\.?|inr)?\s*(\d[\d,]*)", text.lower())
        if m:
            budget = int(m.group(1).replace(",", ""))
        days = None
        m = re.search(r"(\d+)\s*days?", text.lower())
        if m:
            days = int(m.group(1))
        category = None
        lowered = text.lower()
        for kind in ("saree", "basket", "pottery", "gift", "bag", "decor", "storage"):
            if kind in lowered:
                category = "GIFT_BOX" if kind == "gift" else kind.upper()
                break
        customization = any(w in lowered for w in ("custom", "logo", "branded", "personalized", "engraved", "printed"))
        buyer_type = None
        if any(w in lowered for w in ("corporate", "company", "office", "event")):
            buyer_type = "CORPORATE"
        elif any(w in lowered for w in ("hotel", "restaurant", "cafe")):
            buyer_type = "HOSPITALITY"
        elif any(w in lowered for w in ("school", "university", "college", "government", "ngo")):
            buyer_type = "INSTITUTIONAL"
        return {
            "quantity": qty,
            "max_unit_price": budget,
            "delivery_days": days,
            "category": category,
            "customization": customization,
            "buyer_type": buyer_type,
            "confidence": 0.82,
        }

    # ------------------------------------------------------------- explanation

    def explain_price(self, inputs: dict, suggested: float, market_low: float, market_high: float) -> str:
        cost = inputs.get("total_cost", 0)
        labour = inputs.get("labour_cost", 0)
        material = inputs.get("material_cost", 0)
        margin = suggested - cost
        return (
            f"Your material cost (₹{material:,.0f}) plus labour (₹{labour:,.0f}) and other costs "
            f"comes to about ₹{cost:,.0f}. Similar products currently sell between ₹{market_low:,.0f} "
            f"and ₹{market_high:,.0f}. A price of ₹{suggested:,.0f} keeps you competitive while "
            f"earning about ₹{margin:,.0f} per piece for your skill."
        )

    def summarize_reviews(self, reviews: list[dict]) -> Optional[str]:
        if not reviews:
            return None
        positives = sum(1 for r in reviews if (r.get("product_rating") or 0) >= 4)
        themes: list[str] = []
        text = " ".join((r.get("text") or "").lower() for r in reviews)
        for theme, marker in (("quality", ("quality", "well made", "sturdy", "finish")), ("delivery", ("delivery", "arrived", "packed")), ("communication", ("responsive", "communicat", "updates"))):
            if marker and any(mk in text for mk in marker):
                themes.append(theme)
        base = f"{positives} of {len(reviews)} buyers rated this 4+ stars."
        if themes:
            base += " Buyers frequently mention " + " and ".join(themes) + "."
        return base


def _classify_kind(extracted: dict) -> Optional[str]:
    haystack = " ".join(str(extracted.get(k, "")) for k in ("title", "usage", "category", "keywords", "description")).lower()
    for kind, markers in {
        "saree": ("saree", "sari", "சேலை", "साड़ी"),
        "basket": ("basket", "storage", "கூடை", "टोकरी"),
        "pottery": ("pot", "terracotta", "clay", "பானை", "बर्तन"),
    }.items():
        if any(mk in haystack for mk in markers):
            return kind
    return None


def _keywords_for(kind, material, technique, region) -> str:
    kws = ["handmade", "artisan", "indian craft"]
    for item in (kind, material, technique, region):
        if item:
            kws.append(str(item).lower())
    return ", ".join(dict.fromkeys(kws))
