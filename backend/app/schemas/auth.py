"""Auth schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

# 20 official languages + 4 regional packs — must match frontend src/i18n LANGUAGES codes.
SUPPORTED_LANGUAGES = (
    "en", "hi", "bn", "mr", "te", "ta", "gu", "kn", "ml", "or",
    "pa", "as", "ur", "ne", "kok", "ks", "mai", "sat", "mni", "brx",
    "gar", "kfy", "gon", "bhb",
)

_LANG_PATTERN = "^(" + "|".join(SUPPORTED_LANGUAGES) + ")$"


class OTPRequestIn(BaseModel):
    phone: str = Field(min_length=8, max_length=20, examples=["+91 98765 43210"])


class OTPVerifyIn(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    code: str = Field(min_length=4, max_length=8)
    full_name: Optional[str] = Field(default=None, max_length=200)


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: str
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="BUYER", pattern="^(BUYER|B2B_BUYER|ARTISAN)$")


class LoginIn(BaseModel):
    email: str
    password: str


class LanguageIn(BaseModel):
    """UI language preference. Validated against the 24-code registry (20 official + 4 regional)."""

    preferred_language: str = Field(pattern=_LANG_PATTERN)


class UserSettingsIn(BaseModel):
    """Accessibility / voice / region preferences. All optional; only provided fields update."""

    preferred_language: Optional[str] = Field(default=None, pattern=_LANG_PATTERN)
    preferred_voice_language: Optional[str] = Field(default=None, pattern=_LANG_PATTERN)
    voice_enabled: Optional[bool] = None
    easy_mode_enabled: Optional[bool] = None
    font_scale: Optional[float] = Field(default=None, ge=1.0, le=1.5)
    region: Optional[str] = Field(default=None, max_length=80)
    district: Optional[str] = Field(default=None, max_length=80)
    state: Optional[str] = Field(default=None, max_length=80)


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: Optional[str] = None


class TokenPairOut(BaseModel):
    access_token: str
    refresh_token: str
    user: dict
