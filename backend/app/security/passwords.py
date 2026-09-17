"""Password hashing. Never store plaintext; bcrypt with per-hash salt.

Uses the bcrypt library directly (passlib is incompatible with bcrypt>=4.1).
"""

from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
    data = plain.encode("utf-8")[:72]  # bcrypt operates on at most 72 bytes
    return bcrypt.hashpw(data, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False
