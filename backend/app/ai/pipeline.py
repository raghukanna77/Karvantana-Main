"""AI pipeline orchestration (blueprint §45).

Input → validation → preprocessing → provider inference → structured output →
confidence → persistence → (frontend) human review → publish. Every step is
audited in ai_generations / voice_transcripts; raw provider responses are never
production data.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional

from sqlalchemy.orm import Session

from app.ai import confidence as conf
from app.ai.prompts import get_prompt
from app.ai.providers import get_llm, get_speech, get_translation, get_vision
from app.models.ai import AIGeneration, AIUsage, VoiceTranscript
from app.models.catalog import Category

logger = logging.getLogger("karvantana.ai")

# ---------------------------------------------------------------- extraction

MATERIAL_LEXICON = {
    "cotton": ("cotton", "பருத்தி", "कपास", "పట్టి", "ಹತ್ತಿ", "പഞ്ഞി", "সুতি", "सुती", "ਸੂਤੀ"),
    "silk": ("silk", "பட்டு", "रेशम"),
    "bamboo": ("bamboo", "மூங்கில்", "बांस", "వెదురు", "ಬಿದಿರು", "മുള", "বাঁশ", "बांबू", "બાંસ", "ਬਾਂਸ"),
    "clay": ("clay", "terracotta", "களிமண்", "मिट्टी", "বাঁশ"[:0] or "মাটি"),
    "coir": ("coir", "தென்னை நார்", "नारियल"),
    "jute": ("jute", "சணல்", "जूट"),
    "wood": ("wood", "wooden", "மரம்", "लकड़ी"),
    "brass": ("brass", "பித்தளை", "पीतल"),
    "wool": ("wool", "கம்பளி", "ऊन"),
}

TECHNIQUE_LEXICON = {
    "handloom": ("handloom", "handwoven", "கைத்தறி", "हैंडलूम", "हाथ से बुना", "చేతితో నేసిన", "ಕೈಯಿಂದ ನೇಯ್ದ", "হাতে বোনা", "हाताने विणलेले", "હાથથી વણેલું", "ਹੱਥ ਨਾਲ ਬੁਣਿਆ"),
    "handwoven": ("handwoven", "woven by hand"),
    "handmade": ("handmade", "hand made", "கையால்", "हाथ से बना", "చేతిపని", "ಕೈ ಕೆಲಸ", "കൈകൊണ്ടുള്ള", "হাতে তৈরি", "हस्तनिर्मित", "હાથે બનાવેલું", "ਹੱਥ ਨਾਲ ਬਣਿਆ"),
    "natural dye": ("natural dye", "natural colour", "இயற்கை நிறம்", "प्राकृतिक रंग"),
    "hand-thrown": ("hand-thrown", "thrown on the wheel", "wheel"),
}

USAGE_LEXICON = {
    "kitchen storage": ("kitchen", "storage", "சமையலறை", "रसोई", "சேமிப்பு", "भंडारण"),
    "wear": ("wear", "அணிய"),
    "gifting": ("gift", "பரிசு"),
    "home decor": ("decor", "decoration", "home"),
}

COLOUR_LEXICON = ("red", "blue", "green", "yellow", "black", "white", "brown", "natural", "maroon", "indigo",
                  "சிவப்பு", "நீலம்", "பச்சை", "இயற்கை நிறம்", "सफ़ेद", "काला")

DAYS_PATTERN = re.compile(r"(\d+)\s*(?:day|நாள|दिन|நாட்கள்)", re.IGNORECASE)

CATEGORY_RULES: dict[str, tuple[str, ...]] = {
    "saree": ("saree", "sari", "\u0b9a\u0bc7\u0bb2\u0bc8", "\u0938\u093e\u0921\u093c\u0940", "\u0c1a\u0c40\u0c30", "\u0c95\u0cc0\u0cb0\u0cc6", "\u0d38\u0d3e\u0d30\u0d3f", "\u09b6\u09be\u09dc\u09bf", "\u0ab8\u0abe\u0aa1\u0ac0", "\u0a38\u0a3e\u0a5c\u0a4d\u0a39\u0a40"),
    "basket": ("basket", "\u0b95\u0bc2\u0b9f\u0bc8", "\u091f\u094b\u0915\u0930\u0940", "\u0c2c\u0c1f\u0c4d\u0c1f", "\u0cac\u0cc1\u0c9f\u0ccd\u0c9f\u0cbf", "\u0d15\u0d4a\u0d1f\u0d4d\u0d1f", "\u099d\u09c1\u09dc\u09bf", "\u091f\u094b\u0906\u0932\u0940", "\u0a9f\u0acb\u0aaa\u0ab2\u0ac0", "\u0a1f\u0acb\u0a15\u0a30\u0a40"),
    "pottery": ("pot", "terracotta", "clay", "\u0baa\u0bbe\u0ba9\u0bc8", "\u092c\u0930\u094d\u0924\u0928"),
}


def extract_from_texts(transcript_original: str, transcript_en: str) -> dict:
    """Pure extraction helper (no DB) shared by the pipeline and tests."""
    t0 = time.monotonic()
    fields: dict[str, conf.ConfidentValue] = {}

    def find(lexicon: dict[str, tuple[str, ...]], text: str, base_conf: float):
        lowered = text.lower()
        best = None
        for value, markers in lexicon.items():
            for marker in markers:
                if marker in lowered:
                    score = base_conf + 0.05 * len(marker.split())
                    if best is None or score > best.confidence:
                        best = conf.ConfidentValue(value=value, confidence=min(score, 0.97), source=conf.SOURCE_VOICE)
        return best

    material = find(MATERIAL_LEXICON, transcript_original + " " + transcript_en, 0.88)
    if material:
        fields["material"] = material
    technique = find(TECHNIQUE_LEXICON, transcript_original + " " + transcript_en, 0.9)
    if technique:
        fields["technique"] = technique
    usage = find(USAGE_LEXICON, transcript_en + " " + transcript_original, 0.8)
    if usage:
        fields["usage"] = usage
    m = DAYS_PATTERN.search(transcript_original + " " + transcript_en)
    if m:
        fields["production_days"] = conf.ConfidentValue(int(m.group(1)), 0.9, conf.SOURCE_VOICE)
    for colour in COLOUR_LEXICON:
        if colour.lower() in (transcript_original + " " + transcript_en).lower():
            fields["colour"] = conf.ConfidentValue(colour.title(), 0.85, conf.SOURCE_VOICE)
            break
    for cat, markers in CATEGORY_RULES.items():
        if any(mk in transcript_original.lower() for mk in markers):
            fields["category"] = conf.ConfidentValue(cat, 0.9, conf.SOURCE_AI_INFERENCE)
            break
    return {k: v.to_dict() for k, v in fields.items()}


class AIPipeline:
    """Facade the services layer calls; keeps providers and audit plumbing in one place."""

    # ------------------------------------------------------------------ voice

    def process_voice(
        self,
        db: Session,
        *,
        audio_bytes: Optional[bytes],
        text: Optional[str],
        language_hint: Optional[str],
        user_id: Optional[str],
        product_id: Optional[str] = None,
    ) -> dict:
        """Returns {language, transcript, translated, confidence, transcript_id}."""
        t0 = time.monotonic()
        if text:
            speech = __import__("app.ai.providers.speech", fromlist=["transcribe_text_payload"]).transcribe_text_payload(text)
        elif audio_bytes:
            speech = get_speech().transcribe(audio_bytes, language_hint)
        else:
            from app.core.errors import ValidationFailedError

            raise ValidationFailedError("Provide speech audio or text.")
        if language_hint and not text:
            speech.language = language_hint

        translated = ""
        if speech.language != "en":
            translated = get_translation().translate(speech.transcript, speech.language, "en")
        else:
            translated = speech.transcript

        vt = VoiceTranscript(
            user_id=user_id,
            product_id=product_id,
            language=speech.language,
            original_text=speech.transcript,
            translated_text=translated if speech.language != "en" else None,
            confidence=speech.confidence,
            duration_seconds=speech.duration_seconds,
        )
        db.add(vt)
        db.flush()
        self._record_usage(db, task="transcription", provider=get_speech().name, model="demo-stt-v1",
                           latency_ms=int((time.monotonic() - t0) * 1000), success=True,
                           confidence=speech.confidence)
        return {
            "language": speech.language,
            "transcript": speech.transcript,
            "translated": translated,
            "confidence": speech.confidence,
            "transcript_id": vt.id,
        }

    # ------------------------------------------------------------- extraction

    def extract_attributes(self, db: Session, *, transcript_en: str, transcript_original: str, user_id: Optional[str]) -> dict:
        """Lexicon-based attribute extraction with confidence + provenance."""
        t0 = time.monotonic()
        fields: dict[str, conf.ConfidentValue] = {}

        def find(lexicon: dict[str, tuple[str, ...]], text: str, base_conf: float) -> Optional[conf.ConfidentValue]:
            lowered = text.lower()
            best = None
            for value, markers in lexicon.items():
                for marker in markers:
                    if marker in lowered:
                        score = base_conf + 0.05 * len(marker.split())  # longer matches are surer
                        if best is None or score > best.confidence:
                            best = conf.ConfidentValue(value=value, confidence=min(score, 0.97), source=conf.SOURCE_VOICE)
            return best

        material = find(MATERIAL_LEXICON, transcript_original + " " + transcript_en, 0.88)
        if material:
            fields["material"] = material
        technique = find(TECHNIQUE_LEXICON, transcript_original + " " + transcript_en, 0.9)
        if technique:
            fields["technique"] = technique
        usage = find(USAGE_LEXICON, transcript_en + " " + transcript_original, 0.8)
        if usage:
            fields["usage"] = usage

        m = DAYS_PATTERN.search(transcript_original + " " + transcript_en)
        if m:
            fields["production_days"] = conf.ConfidentValue(int(m.group(1)), 0.9, conf.SOURCE_VOICE)

        for colour in COLOUR_LEXICON:
            if colour.lower() in (transcript_original + " " + transcript_en).lower():
                fields["colour"] = conf.ConfidentValue(colour.title(), 0.85, conf.SOURCE_VOICE)
                break

        category = None
        for cat, markers in CATEGORY_RULES.items():
            if any(mk in transcript_original.lower() for mk in markers):
                category = conf.ConfidentValue(cat, 0.9, conf.SOURCE_AI_INFERENCE)
                break
        if category:
            fields["category"] = category

        # language of the artisan (from script) helps region inference
        out = {k: v.to_dict() for k, v in fields.items()}
        self._record_usage(db, task="attribute_extraction", provider="demo-nlp", model="lexicon-v1",
                           latency_ms=int((time.monotonic() - t0) * 1000), success=True,
                           confidence=conf.average_confidence(list(fields.values())))
        self._audit(db, task="attribute_extraction", user_id=user_id, provider="demo-nlp",
                    model="lexicon-v1", prompt_key="attribute_extractor",
                    input_payload={"transcript_en": transcript_en[:500]}, output=out,
                    confidence=conf.average_confidence(list(fields.values())))
        return out

    # -------------------------------------------------------------- catalogue

    def generate_catalogue(
        self, db: Session, *, extracted: dict, artisan_name: str, region: str,
        user_id: Optional[str], product_id: Optional[str] = None,
    ) -> dict:
        t0 = time.monotonic()
        prompt = get_prompt("catalogue_generator")
        llm = get_llm()
        # Structured inputs only — the raw transcript is NOT pasted into generation.
        structured = {k: v["value"] if isinstance(v, dict) else v for k, v in extracted.items()}
        catalogue = llm.generate_catalogue(structured, artisan_name, region)
        latency = int((time.monotonic() - t0) * 1000)
        overall = 0.86
        self._record_usage(db, task="catalogue", provider=llm.name, model=llm.model,
                           latency_ms=latency, success=True, confidence=overall)
        generation = self._audit(db, task="catalogue", user_id=user_id, provider=llm.name,
                                 model=llm.model, prompt_key=prompt.key,
                                 input_payload={"extracted": structured}, output=catalogue,
                                 confidence=overall, product_id=product_id)
        catalogue["generation_id"] = generation.id
        catalogue["prompt_version"] = prompt.version
        catalogue["confidence"] = overall
        return catalogue

    def regenerate_field(self, db: Session, *, field: str, catalogue: dict, extracted: dict,
                         artisan_name: str, region: str, user_id: Optional[str]) -> dict:
        """Field-level regeneration; approved fields are preserved (blueprint §121)."""
        fresh = self.generate_catalogue(db, extracted=extracted, artisan_name=artisan_name,
                                        region=region, user_id=user_id)
        if field in fresh and field in ("title", "short_description", "description", "keywords", "highlights"):
            return {**catalogue, field: fresh[field]}
        return catalogue

    # ------------------------------------------------------------------ audit

    def _audit(self, db: Session, *, task: str, user_id: Optional[str], provider: str,
               model: str, prompt_key: str, input_payload: dict, output: dict,
               confidence: Optional[float], product_id: Optional[str] = None) -> AIGeneration:
        prompt = get_prompt(prompt_key)
        row = AIGeneration(
            user_id=user_id, product_id=product_id, task=task, provider=provider, model=model,
            prompt_version=prompt.version, input_payload=input_payload, output=output,
            confidence=confidence, status="SUCCESS",
        )
        db.add(row)
        db.flush()
        return row

    def _record_usage(self, db: Session, *, task: str, provider: str, model: str,
                      latency_ms: int, success: bool, confidence: Optional[float]) -> None:
        db.add(AIUsage(task=task, provider=provider, model=model, latency_ms=latency_ms,
                       success=success, confidence=confidence, estimated_cost_usd=0.0))


pipeline = AIPipeline()
