"""Confidence-tagged values (blueprint §17).

Every AI-derived structured field keeps value + confidence + source.
Low-confidence values never silently become facts — the UI asks the artisan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


SOURCE_VOICE = "VOICE"
SOURCE_IMAGE = "IMAGE"
SOURCE_ARTISAN_INPUT = "ARTISAN_INPUT"
SOURCE_AI_INFERENCE = "AI_INFERENCE"
SOURCE_SYSTEM = "SYSTEM"


@dataclass
class ConfidentValue:
    value: Any
    confidence: float  # 0..1
    source: str = SOURCE_AI_INFERENCE

    def to_dict(self) -> dict:
        return {"value": self.value, "confidence": round(self.confidence, 2), "source": self.source}


CONFIRM_THRESHOLD = 0.75  # below this the artisan is explicitly asked to confirm


def needs_confirmation(cv: ConfidentValue) -> bool:
    return cv.confidence < CONFIRM_THRESHOLD


def average_confidence(values: list[ConfidentValue]) -> Optional[float]:
    if not values:
        return None
    return sum(v.confidence for v in values) / len(values)
