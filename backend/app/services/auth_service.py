"""Authentication service: OTP + password flows, JWT issuance, audit trail."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthenticationError, ConflictError, NotFoundError, RateLimitedError, ValidationFailedError
from app.core.logging import new_request_id
from app.models.analytics import AuditLog
from app.models.user import OTPCode, RefreshToken, User
from app.security.jwt import create_access_token, create_refresh_token, decode_token
from app.security.passwords import hash_password, verify_password
from app.security.rbac import Role

_OTP_TTL_MINUTES = 10
_MAX_OTP_ATTEMPTS = 5


def _normalize_phone(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        raise ValidationFailedError("Enter a valid mobile number.")
    return digits[-10:]


def _audit(db: Session, *, actor_id: Optional[str], action: str, detail: Optional[dict] = None) -> None:
    db.add(AuditLog(actor_id=actor_id, action=action, entity_type="auth", detail=detail))


class AuthService:
    # ------------------------------------------------------------------ OTP

    def request_otp(self, db: Session, phone: str) -> dict:
        normalized = _normalize_phone(phone)
        recent = (
            db.query(OTPCode)
            .filter(OTPCode.phone == normalized, OTPCode.created_at > datetime.utcnow() - timedelta(seconds=45))
            .first()
        )
        if recent:
            raise RateLimitedError("Please wait a minute before requesting another code.")

        code = f"{secrets.randbelow(1000000):06d}"
        row = OTPCode(
            phone=normalized,
            code_hash=hashlib.sha256(code.encode()).hexdigest(),
            expires_at=datetime.utcnow() + timedelta(minutes=_OTP_TTL_MINUTES),
        )
        db.add(row)
        db.flush()
        # Demo delivery: the code is returned in dev/demo only. In production an
        # SMS provider adapter sends it and the response omits it entirely.
        demo_mode = get_settings().ENV != "production"
        return {
            "sent": True,
            "expires_in_minutes": _OTP_TTL_MINUTES,
            "demo_code": code if demo_mode else None,
            "delivery": "demo" if demo_mode else "sms",
        }

    def verify_otp(self, db: Session, phone: str, code: str, full_name: Optional[str] = None) -> dict:
        normalized = _normalize_phone(phone)
        row = (
            db.query(OTPCode)
            .filter(OTPCode.phone == normalized, OTPCode.consumed_at.is_(None))
            .order_by(OTPCode.created_at.desc())
            .first()
        )
        if row is None:
            raise AuthenticationError("Request a new code and try again.")
        if row.expires_at < datetime.utcnow():
            raise AuthenticationError("That code has expired. Request a new one.")
        if row.attempts >= _MAX_OTP_ATTEMPTS:
            raise AuthenticationError("Too many incorrect attempts. Request a new code.")
        expected = row.code_hash
        if not hmac.compare_digest(hashlib.sha256(code.strip().encode()).hexdigest(), expected):
            row.attempts += 1
            raise AuthenticationError("That code is incorrect. Please check and try again.")
        row.consumed_at = datetime.utcnow()

        user = db.query(User).filter(User.phone == normalized).first()
        created = False
        if user is None:
            if not full_name or not full_name.strip():
                raise ValidationFailedError("Tell us your name to create your account.", details={"field": "full_name"})
            user = User(phone=normalized, full_name=full_name.strip()[:200], role=Role.ARTISAN.value)
            db.add(user)
            db.flush()
            created = True
        if not user.is_active:
            raise AuthenticationError("This account has been deactivated. Contact support.")
        user.last_login_at = datetime.utcnow()
        _audit(db, actor_id=user.id, action="AUTH_OTP_LOGIN", detail={"created": created})
        return self._tokens_for(db, user)

    # -------------------------------------------------------------- password

    def register(self, db: Session, *, full_name: str, email: str, password: str, role: str = Role.BUYER.value) -> dict:
        email = email.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValidationFailedError("Enter a valid email address.", details={"field": "email"})
        if len(password) < 8:
            raise ValidationFailedError("Password must be at least 8 characters.", details={"field": "password"})
        if db.query(User).filter(User.email == email).first():
            raise ConflictError("An account with this email already exists. Try signing in.")
        if role not in (Role.BUYER.value, Role.B2B_BUYER.value, Role.ARTISAN.value):
            # Role escalation guard: privileged roles are provisioned internally only.
            raise ValidationFailedError("Choose buyer or artisan to create an account.")
        user = User(
            email=email,
            full_name=full_name.strip()[:200],
            hashed_password=hash_password(password),
            role=role,
        )
        db.add(user)
        db.flush()
        _audit(db, actor_id=user.id, action="AUTH_REGISTER", detail={"role": role})
        return self._tokens_for(db, user)

    def login(self, db: Session, *, email: str, password: str) -> dict:
        user = db.query(User).filter(User.email == email.strip().lower()).first()
        if user is None or not user.hashed_password or not verify_password(password, user.hashed_password):
            # Uniform error: never reveal whether the account exists.
            raise AuthenticationError("Email or password is incorrect.")
        if not user.is_active:
            raise AuthenticationError("This account has been deactivated. Contact support.")
        user.last_login_at = datetime.utcnow()
        _audit(db, actor_id=user.id, action="AUTH_LOGIN")
        return self._tokens_for(db, user)

    # --------------------------------------------------------------- tokens

    def _tokens_for(self, db: Session, user: User) -> dict:
        jti = str(uuid.uuid4())
        rt = RefreshToken(
            user_id=user.id,
            jti=jti,
            expires_at=datetime.utcnow() + timedelta(days=get_settings().REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(rt)
        db.flush()
        return {
            "access_token": create_access_token(user.id, user.role),
            "refresh_token": create_refresh_token(user.id, jti),
            "user": self.public_user(user),
        }

    def refresh(self, db: Session, refresh_token: str) -> dict:
        claims = decode_token(refresh_token, expected_type="refresh")
        row = db.query(RefreshToken).filter(RefreshToken.jti == claims["jti"]).first()
        if row is None or row.revoked_at is not None or row.expires_at < datetime.utcnow():
            raise AuthenticationError("Session expired. Please sign in again.")
        row.revoked_at = datetime.utcnow()  # rotation
        user = db.query(User).filter(User.id == claims["sub"]).first()
        if user is None or not user.is_active:
            raise AuthenticationError("Session expired. Please sign in again.")
        return self._tokens_for(db, user)

    def logout(self, db: Session, refresh_token: Optional[str]) -> None:
        if not refresh_token:
            return
        try:
            claims = decode_token(refresh_token, expected_type="refresh")
        except AuthenticationError:
            return
        row = db.query(RefreshToken).filter(RefreshToken.jti == claims["jti"]).first()
        if row:
            row.revoked_at = datetime.utcnow()

    # ---------------------------------------------------------------- misc

    def get_active_user(self, db: Session, user_id: str) -> Optional[User]:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.is_active:
            return user
        return None

    @staticmethod
    def public_user(user: User) -> dict:
        return {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "preferred_language": user.preferred_language,
        }


auth_service = AuthService()
