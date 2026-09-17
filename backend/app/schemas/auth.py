"""Auth schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


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


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: Optional[str] = None


class TokenPairOut(BaseModel):
    access_token: str
    refresh_token: str
    user: dict
