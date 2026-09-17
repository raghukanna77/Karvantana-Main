"""JWT creation/verification. Short-lived access tokens, rotating refresh tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.errors import AuthenticationError

_SETTINGS = get_settings()


def _create(payload: dict[str, Any], expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        **payload,
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type,
        "iss": "karvantana",
    }
    return jwt.encode(claims, _SETTINGS.JWT_SECRET, algorithm=_SETTINGS.JWT_ALGORITHM)


def create_access_token(user_id: str, role: str) -> str:
    return _create({"sub": user_id, "role": role}, timedelta(minutes=_SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(user_id: str, jti: str) -> str:
    return _create({"sub": user_id, "jti": jti}, timedelta(days=_SETTINGS.REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(token, _SETTINGS.JWT_SECRET, algorithms=[_SETTINGS.JWT_ALGORITHM], issuer="karvantana")
    except JWTError as exc:
        raise AuthenticationError("Your session has expired. Please sign in again.") from exc
    if claims.get("type") != expected_type:
        raise AuthenticationError("Invalid token type.")
    return claims
