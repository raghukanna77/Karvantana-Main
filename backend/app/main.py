"""KARVANTANA FastAPI application.

From Craft to Commerce — AI-powered digital business manager for artisans.
"""

from __future__ import annotations

import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, new_request_id
from app.api.v1 import ai, analytics, artisans, auth, commerce, orders, payments, products, sih, whatsapp
import app.models  # noqa: F401  register all models with Base.metadata

settings = get_settings()
configure_logging()


def create_app() -> FastAPI:
    app = FastAPI(
        title="KARVANTANA API",
        version=__version__,
        description=(
            "AI-powered digital business manager for marginalized artisans — "
            "from craft to commerce. All AI/integration providers have "
            "clearly-labeled demo implementations; no endpoint fakes success."
        ),
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Idempotency-Key"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = new_request_id()
        start = time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    register_error_handlers(app)

    # Media (local storage backend; S3 in production with signed URLs)
    media_dir = os.path.abspath(settings.MEDIA_DIR)
    os.makedirs(media_dir, exist_ok=True)
    app.mount("/media", StaticFiles(directory=media_dir), name="media")

    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(artisans.router, prefix=api_prefix)
    app.include_router(products.router, prefix=api_prefix)
    app.include_router(ai.router, prefix=api_prefix)
    app.include_router(orders.router, prefix=api_prefix)
    app.include_router(payments.router, prefix=api_prefix)
    app.include_router(commerce.router, prefix=api_prefix)
    app.include_router(analytics.router, prefix=api_prefix)
    app.include_router(sih.router, prefix=api_prefix)
    app.include_router(whatsapp.router, prefix=api_prefix)

    @app.get("/api/health", tags=["system"], summary="Health check")
    def health():
        return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV,
                "version": __version__,
                "providers": {
                    "ai": settings.AI_PROVIDER,
                    "payments": settings.PAYMENT_PROVIDER,
                    "logistics": settings.LOGISTICS_PROVIDER,
                }}

    # Ensure database tables exist and seed demo data if empty on startup
    from app.core.database import Base, engine, SessionLocal
    from app.models.user import User
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        if db.query(User).filter(User.is_demo.is_(True)).count() == 0:
            import sys
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if parent_dir not in sys.path:
                sys.path.append(parent_dir)
            try:
                import seed_demo
                seed_demo.seed()
            except Exception:
                pass
        db.close()
    except Exception:
        pass

    return app


app = create_app()
