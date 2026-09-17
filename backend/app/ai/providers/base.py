"""Provider interfaces. KARVANTANA is provider-agnostic: real vendors plug in
here without touching business logic (blueprint §44, §115)."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SpeechResult:
    language: str
    transcript: str
    confidence: float
    duration_seconds: Optional[float] = None


@dataclass
class VisionQuality:
    score: int  # 0..100
    checks: list[dict] = field(default_factory=list)  # [{label, passed, detail}]


@dataclass
class ImageEnhancement:
    enhanced_path: str
    operations: list[str] = field(default_factory=list)


class LLMProvider(abc.ABC):
    name = "llm"

    @abc.abstractmethod
    def generate_structured(self, task: str, prompt_version: str, system: str, user: str, schema_hint: dict) -> dict:
        """Return a schema-validated structured dict; implementations must never
        return raw free text as production data."""


class SpeechProvider(abc.ABC):
    name = "speech"

    @abc.abstractmethod
    def transcribe(self, audio_bytes: bytes, language_hint: Optional[str] = None) -> SpeechResult: ...


class TranslationProvider(abc.ABC):
    name = "translation"

    @abc.abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str = "en") -> str: ...

    @abc.abstractmethod
    def detect_language(self, text: str) -> str: ...


class VisionProvider(abc.ABC):
    name = "vision"

    @abc.abstractmethod
    def analyze_quality(self, image_bytes: bytes) -> VisionQuality: ...

    @abc.abstractmethod
    def enhance(self, image_bytes: bytes, operations: Optional[list[str]] = None) -> ImageEnhancement: ...

    @abc.abstractmethod
    def background_clean(self, image_bytes: bytes) -> ImageEnhancement: ...


class EmbeddingProvider(abc.ABC):
    name = "embedding"

    @abc.abstractmethod
    def embed_text(self, text: str) -> list[float]: ...


class RecommendationProvider(abc.ABC):
    name = "recommendation"

    @abc.abstractmethod
    def rank_products(self, query_features: dict, candidates: list[dict]) -> list[tuple[dict, float, list[str]]]:
        """Return (candidate, score, match_reasons) sorted by score."""
