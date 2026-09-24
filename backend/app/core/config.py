"""Application configuration.

All secrets come from environment variables (see .env.example). Defaults are
development-only and clearly unsafe-for-production where applicable.
"""

from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Identity
    APP_NAME: str = "KARVANTANA"
    APP_TAGLINE: str = "From Craft to Commerce"
    ENV: str = "development"  # development | demo | staging | production

    # Data
    DATABASE_URL: str = "sqlite:///./karvantana.db"

    # Auth
    JWT_SECRET: str = "dev-only-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # Network
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Provider selection — every integration is provider-agnostic with a
    # clearly-labeled demo implementation available without credentials.
    AI_PROVIDER: str = "demo"  # demo | openai
    PAYMENT_PROVIDER: str = "demo"  # demo | razorpay
    LOGISTICS_PROVIDER: str = "demo"
    STORAGE_BACKEND: str = "local"  # local | s3
    MEDIA_DIR: str = "./media"

    # Rate limits (requests/minute) per scope
    RATE_LIMIT_AI_PER_MIN: int = 12
    RATE_LIMIT_AUTH_PER_MIN: int = 10
    RATE_LIMIT_SEARCH_PER_MIN: int = 60

    # Feature flags (controlled rollout; admin-overridable at runtime later)
    FEATURE_VOICE_CATALOGUE: bool = True
    FEATURE_AI_PRICING: bool = True
    FEATURE_B2B: bool = True
    FEATURE_AI_ASSISTANT: bool = True
    FEATURE_ONDC_EXPORT: bool = True
    FEATURE_WHATSAPP: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        if not self.is_production:
            dev_origins = ["capacitor://localhost", "http://localhost", "https://localhost", "http://localhost:5173", "http://127.0.0.1:5173"]
            for o in dev_origins:
                if o not in origins:
                    origins.append(o)
        return origins

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
