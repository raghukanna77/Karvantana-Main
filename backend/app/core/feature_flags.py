"""Feature flags for controlled rollout.

Backed by Settings env vars; an admin-level runtime override store can be added
on top without changing call sites.
"""

from __future__ import annotations

from typing import Optional

from app.core.config import get_settings

_FLAG_MAP = {
    "VOICE_CATALOGUE": "FEATURE_VOICE_CATALOGUE",
    "AI_PRICING": "FEATURE_AI_PRICING",
    "B2B": "FEATURE_B2B",
    "AI_ASSISTANT": "FEATURE_AI_ASSISTANT",
    "ONDC_EXPORT": "FEATURE_ONDC_EXPORT",
    "WHATSAPP": "FEATURE_WHATSAPP",
}


def is_enabled(flag: str) -> bool:
    attr = _FLAG_MAP.get(flag.upper())
    if attr is None:
        return False
    return bool(getattr(get_settings(), attr, False))


def all_flags() -> dict[str, bool]:
    return {flag: is_enabled(flag) for flag in _FLAG_MAP}


def require_flag(flag: str, message: Optional[str] = None) -> None:
    from app.core.errors import AppError

    if not is_enabled(flag):
        raise AppError(
            message or f"The {flag.lower().replace('_', ' ')} feature is not enabled on this deployment.",
            code="FEATURE_DISABLED",
        )
