"""Request-scoped auth dependencies.

get_current_user      — validates access token, loads user
require_roles(...)    — role gate
require_ownership     — object ownership gate (usage: dep over loaded object)
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.models.user import User
from app.security.jwt import decode_token


def _extract_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise AuthenticationError("Please sign in to continue.")
    return auth.removeprefix("Bearer ").strip()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    from app.services.auth_service import auth_service  # late import avoids cycles

    token = _extract_token(request)
    claims = decode_token(token, expected_type="access")
    user = auth_service.get_active_user(db, claims["sub"])
    if user is None:
        raise AuthenticationError("Account not found or deactivated.")
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        return get_current_user(request, db)
    except Exception:
        return None


def require_roles(*roles: str) -> Callable[..., Any]:
    allowed = {r if isinstance(r, str) else r.value for r in roles}

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise PermissionDeniedError("You don't have access to this area.")
        return user

    return dependency


def ensure_ownership(obj: Any, user: User, field: str = "user_id") -> None:
    owner = getattr(obj, field, None)
    admin_bypass = user.role == "ADMIN"
    if owner is None:
        # Objects like Product carry artisan_id — resolved by callers with custom fields.
        raise PermissionDeniedError("You can only manage your own records.")
    if owner != user.id and not admin_bypass:
        raise PermissionDeniedError("You can only manage your own records.")
