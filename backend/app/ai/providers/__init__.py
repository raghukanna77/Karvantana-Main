"""AI provider factory — selects implementations from settings.

Real vendors plug in by implementing the interfaces in base.py and adding a
branch here. The demo providers are always available and clearly labeled.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings


@lru_cache
def get_llm():
    if get_settings().AI_PROVIDER == "openai":  # future: real branch
        raise NotImplementedError("Set OPENAI_API_KEY and implement OpenAI LLM provider.")
    from app.ai.providers.llm import DemoLLMProvider

    return DemoLLMProvider()


@lru_cache
def get_vision():
    from app.ai.providers.vision import DemoVisionProvider

    return DemoVisionProvider()


@lru_cache
def get_speech():
    from app.ai.providers.speech import DemoSpeechProvider

    return DemoSpeechProvider()


@lru_cache
def get_translation():
    from app.ai.providers.translation import DemoTranslationProvider

    return DemoTranslationProvider()
