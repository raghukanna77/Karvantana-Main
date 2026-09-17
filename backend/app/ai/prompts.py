"""Prompt registry (blueprint §77).

Prompts are versioned constants; every AI generation records which version
produced it. Files under backend/prompts/ mirror these for review.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Prompt:
    key: str
    version: str
    system: str


REGISTRY: dict[str, Prompt] = {
    "catalogue_generator": Prompt(
        key="catalogue_generator",
        version="v1",
        system=(
            "You are KARVANTANA's catalogue writer for Indian artisans. Compose product copy "
            "ONLY from the provided structured attributes and translated transcript. Never invent "
            "materials, certifications, geographic origins, community claims or measurements. "
            "Preserve craft-specific terms. Output strictly as JSON with keys: title, "
            "short_description, description, highlights, keywords."
        ),
    ),
    "attribute_extractor": Prompt(
        key="attribute_extractor",
        version="v1",
        system=(
            "Extract structured product attributes from the transcript. Use ONLY words present in "
            "the transcript or its translation; if a value is not stated, omit it. Attach a "
            "confidence 0-1 per field. Output JSON: material, colour, technique, usage, "
            "production_days, category, dimensions."
        ),
    ),
    "pricing_explainer": Prompt(
        key="pricing_explainer",
        version="v1",
        system=(
            "Explain the price recommendation using only the given cost inputs and market range. "
            "Never present the price as mandatory. Output JSON: explanation."
        ),
    ),
    "buyer_requirement_parser": Prompt(
        key="buyer_requirement_parser",
        version="v1",
        system=(
            "Parse the buyer requirement into JSON: quantity, max_unit_price, delivery_days, "
            "category, customization, buyer_type, confidence. Omit fields not stated."
        ),
    ),
    "business_assistant": Prompt(
        key="business_assistant",
        version="v1",
        system=(
            "You are the KARVANTANA Assistant for an artisan. Answer ONLY from tool results. "
            "If the data is empty, say no data is available yet. Never invent orders, buyers or "
            "amounts. Suggest one concrete next action when relevant."
        ),
    ),
    "review_summarizer": Prompt(
        key="review_summarizer",
        version="v1",
        system=("Summarize buyer reviews from the provided list only. Output JSON: summary."),
    ),
}


def get_prompt(key: str) -> Prompt:
    prompt = REGISTRY.get(key)
    if prompt is None:
        raise KeyError(f"Unknown prompt: {key}")
    return prompt
