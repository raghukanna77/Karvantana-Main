"""AI endpoints (/api/v1/ai). All routes are artisan-gated and rate-limited."""

from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.ai.assistant import assistant_service
from app.ai.pipeline import pipeline
from app.core.database import get_db
from app.core.errors import ValidationFailedError
from app.core.feature_flags import require_flag
from app.models.profile import ArtisanProfile
from app.models.user import User
from app.schemas.product import (
    CatalogueGenerateIn, PricingInputsIn, RegenerateFieldIn, VoiceIn,
)
from app.security.dependencies import get_current_user, require_roles


def _record_usage(db: Session, *, task: str, latency_ms: int) -> None:
    """Usage row for AI governance (admin monitoring, blueprint §81)."""
    from app.ai.providers import get_llm
    from app.models.ai import AIUsage

    llm = get_llm()
    db.add(AIUsage(task=task, provider=llm.name, model=getattr(llm, "model_name", llm.name),
                   latency_ms=latency_ms, success=True, estimated_cost_usd=0.0))
    db.flush()
from app.security.rate_limit import enforce
from app.services.pricing_service import PricingInputs, pricing_service
from app.services.product_service import product_service

router = APIRouter(prefix="/ai", tags=["ai"])


def _artisan(db: Session, user: User) -> ArtisanProfile:
    profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
    if profile is None:
        raise ValidationFailedError("Complete artisan onboarding to use AI features.")
    return profile


@router.post("/voice/transcribe", summary="Process a voice note or transcript")
def voice(payload: VoiceIn, request: Request, user: User = Depends(require_roles("ARTISAN", "ADMIN")),
          db: Session = Depends(get_db)):
    require_flag("VOICE_CATALOGUE")
    enforce("ai", user.id)
    if not payload.text and not payload.language_hint:
        raise ValidationFailedError("Provide the spoken text captured on the device.")
    result = pipeline.process_voice(
        db, audio_bytes=None, text=payload.text, language_hint=payload.language_hint,
        user_id=user.id,
    )
    extracted = pipeline.extract_attributes(
        db, transcript_en=result["translated"], transcript_original=result["transcript"], user_id=user.id
    )
    result["extracted"] = extracted
    return result


@router.post("/voice/upload", summary="Upload an audio note for transcription")
async def voice_upload(request: Request, file: UploadFile = File(...),
                       language: Optional[str] = Form(None),
                       user: User = Depends(require_roles("ARTISAN", "ADMIN")),
                       db: Session = Depends(get_db)):
    require_flag("VOICE_CATALOGUE")
    enforce("ai", user.id)
    audio = await file.read()
    if len(audio) > 8 * 1024 * 1024:
        raise ValidationFailedError("Voice notes can be up to 8 MB.")
    result = pipeline.process_voice(db, audio_bytes=audio, text=None, language_hint=language, user_id=user.id)
    extracted = pipeline.extract_attributes(
        db, transcript_en=result["translated"], transcript_original=result["transcript"], user_id=user.id
    )
    result["extracted"] = extracted
    return result


@router.post("/catalogue/generate", summary="Generate catalogue copy from structured extraction")
def catalogue_generate(payload: CatalogueGenerateIn, request: Request,
                       user: User = Depends(require_roles("ARTISAN", "ADMIN")),
                       db: Session = Depends(get_db)):
    enforce("ai", user.id)
    product = product_service.get_owned_product(db, payload.product_id, user)
    profile = _artisan(db, user)
    region = ", ".join(filter(None, [profile.city or profile.village, profile.state])) or ""
    structured = pipeline.extract_attributes(
        db, transcript_en=payload.transcript_en, transcript_original=payload.transcript_original,
        user_id=user.id,
    )
    catalogue = pipeline.generate_catalogue(
        db, extracted=structured, artisan_name=profile.display_name, region=region,
        user_id=user.id, product_id=product.id,
    )
    catalogue["extracted"] = structured
    return catalogue


@router.post("/catalogue/regenerate-field", summary="Regenerate a single catalogue field")
def catalogue_regenerate(payload: RegenerateFieldIn, request: Request,
                         user: User = Depends(require_roles("ARTISAN", "ADMIN")),
                         db: Session = Depends(get_db)):
    enforce("ai", user.id)
    # Regeneration works off the last stored generation for this product
    from app.models.ai import AIGeneration

    profile = _artisan(db, user)
    latest = (
        db.query(AIGeneration)
        .filter(AIGeneration.task == "catalogue")
        .order_by(AIGeneration.created_at.desc())
        .first()
    )
    if latest is None or latest.output is None:
        raise ValidationFailedError("Generate a catalogue first.")
    region = profile.state or ""
    fresh = pipeline.generate_catalogue(
        db, extracted=latest.input_payload.get("extracted", {}),
        artisan_name=profile.display_name, region=region, user_id=user.id,
    )
    field = payload.field
    updated = dict(latest.output or {})
    if field in fresh:
        updated[field] = fresh[field]
    else:
        raise ValidationFailedError("That field can't be regenerated.")
    return updated


@router.post("/pricing/recommend", summary="Smart pricing recommendation with explanation")
def pricing_recommend(payload: PricingInputsIn, request: Request,
                      user: User = Depends(require_roles("ARTISAN", "ADMIN")),
                      db: Session = Depends(get_db)):
    require_flag("AI_PRICING")
    enforce("ai", user.id)
    inputs = PricingInputs(**payload.model_dump())
    rec = pricing_service.recommend(db, user=user, inputs=inputs)
    return {
        "estimated_cost": rec.estimated_cost,
        "market_low": rec.market_low,
        "market_high": rec.market_high,
        "suggested_price": rec.suggested_price,
        "estimated_margin": rec.estimated_margin,
        "margin_pct": rec.margin_pct,
        "demand_signal": rec.demand_signal,
        "explanation": rec.explanation,
        "contributions": rec.contributions,
    }


@router.post("/images/analyze", summary="Analyze image quality")
async def images_analyze(request: Request, file: UploadFile = File(...),
                         user: User = Depends(require_roles("ARTISAN", "ADMIN")),
                         db: Session = Depends(get_db)):
    enforce("ai", user.id)
    data = await file.read()
    vision = __import__("app.ai.providers", fromlist=["get_vision"]).get_vision()
    result = vision.analyze_quality(data)
    return {"score": result.score, "checks": result.checks}


@router.post("/images/enhance", summary="Enhance / clean background (non-destructive)")
async def images_enhance(request: Request, file: UploadFile = File(...),
                         mode: str = Form("enhance"),  # enhance | background
                         user: User = Depends(require_roles("ARTISAN", "ADMIN")),
                         db: Session = Depends(get_db)):
    enforce("ai", user.id)
    data = await file.read()
    if not data:
        raise ValidationFailedError("Choose a photo first.")
    vision = __import__("app.ai.providers", fromlist=["get_vision"]).get_vision()
    result = vision.background_clean(data) if mode == "background" else vision.enhance(data)
    from app.services.media_service import sniff_image_mime

    return {"url": result.enhanced_path, "operations": result.operations, "mode": mode}


@router.post("/assistant/ask", summary="Ask the KARVANTANA business assistant")
def assistant_ask(payload: dict, request: Request,
                  user: User = Depends(require_roles("ARTISAN", "ADMIN")),
                  db: Session = Depends(get_db)):
    require_flag("AI_ASSISTANT")
    enforce("ai", user.id)
    _start = time.time()
    question = str(payload.get("question", "")).strip()[:500]
    if not question:
        raise ValidationFailedError("Ask a question about your business.")
    result = assistant_service.ask(db, user, question)
    _record_usage(db, task="assistant", latency_ms=int((time.time() - _start) * 1000))
    return result


@router.post("/requirements/parse", summary="Parse a buyer requirement (B2B)")
def parse_requirement(payload: dict, request: Request,
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce("ai", user.id)
    started = time.time()
    text = str(payload.get("text", "")).strip()[:1000]
    if not text:
        raise ValidationFailedError("Describe your requirement in a sentence.")
    from app.ai.providers import get_llm

    parsed = get_llm().parse_buyer_requirement(text)
    _record_usage(db, task="requirement_parse", latency_ms=int((time.time() - started) * 1000))
    return parsed
