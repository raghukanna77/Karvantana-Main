"""WhatsAppBot — the conversation state machine (feature spec steps 1–6).

This module decides WHAT the bot says and WHICH backend pipeline steps run; it
contains no AI logic of its own (pipeline/pricing/product services are reused
verbatim) and no delivery logic of its own (an IMessagingChannel sends). States:

  AWAITING_PHOTO → AWAITING_VOICE → PROCESSING → REVIEW → (publish) → IDLE
                                                     └→ EDITING → REVIEW

Sessions persist per phone number in WhatsAppSession, so an interrupted
conversation resumes exactly where it stopped.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.pipeline import pipeline
from app.core.errors import ValidationFailedError
from app.models.product import Product, ProductLifecycle
from app.models.profile import ArtisanProfile
from app.models.user import User
from app.models.whatsapp import WhatsAppSession, WhatsAppState
from app.security.rate_limit import enforce
from app.services import messaging_channel as mc
from app.services.media_service import sniff_image_mime
from app.services.pricing_service import PricingInputs, pricing_service
from app.services.product_service import product_service

GREETING = (
    "Namaste! 🙏 I'm the KARVANTANA Assistant. I help you sell your handmade work "
    "online — no app needed, right here in chat.\n\n"
    "Let's list your first product. 📸 Send me a *photo* of it."
)
ASK_VOICE = (
    "Photo received ✅\n\nNow please send a *voice note* describing the product — "
    "in any language you like: what it is, what it's made of, how it's made, and "
    "how long it takes. Just talk naturally."
)
PROCESSING_NOTE = "Processing your product… (enhancing the photo, hearing your voice note, writing the listing)"
EDIT_PROMPT = "Sure — what would you like to change? Send a voice note or just type it."
PUBLISHED_LINK = "/product/{pid}"

# Canonical quick-reply button ids (surfaced to the client verbatim)
BTN_PUBLISH = "publish"
BTN_EDIT = "edit"


class WhatsAppBot:
    """Pure state machine: inbound message → session mutation + outbound messages."""

    # Negation guard for corrections: "not cotton, actually jute" must not let
    # the lexicon re-pick "cotton" from the negated phrase (demo-grade, en-only).
    _NEGATION = re.compile(r"\bnot\s+\w+", re.IGNORECASE)
    """Pure state machine: inbound message → session mutation + outbound messages."""

    # ------------------------------------------------------------- bootstrap

    def get_or_create_session(self, db: Session, user: User, phone: str) -> WhatsAppSession:
        session = db.query(WhatsAppSession).filter(WhatsAppSession.phone == phone).first()
        if session is None:
            session = WhatsAppSession(phone=phone, user_id=user.id)
            db.add(session)
            db.flush()
        elif session.user_id != user.id:
            # Phone re-bound to a different account (e.g. re-registration): rebind.
            session.user_id = user.id
        return session

    def ensure_greeting(self, db: Session, session: WhatsAppSession, channel: mc.IMessagingChannel) -> list[dict]:
        """Send the greeting the first time a phone ever contacts the bot."""
        if session.current_state != WhatsAppState.AWAITING_PHOTO or session.draft_listing_id is not None:
            return []
        msgs = [mc.text_message(GREETING)]
        return channel.send(session.phone, msgs)

    # --------------------------------------------------------------- inbound

    def handle_inbound(
        self,
        db: Session,
        user: User,
        session: WhatsAppSession,
        channel: mc.IMessagingChannel,
        *,
        text: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        voice_bytes: Optional[bytes] = None,
        button_id: Optional[str] = None,
        language_hint: Optional[str] = None,
    ) -> dict:
        """Route one inbound exchange. Returns {"messages": [...], "state": ...}."""
        profile = self._profile(db, user)
        state = session.current_state
        out: list[mc.OutboundMessage] = []

        if button_id:
            if state in (WhatsAppState.REVIEW, WhatsAppState.IDLE) and button_id == BTN_PUBLISH:
                return self._publish(db, user, profile, session, channel)
            if state in (WhatsAppState.REVIEW, WhatsAppState.IDLE) and button_id == BTN_EDIT:
                return self._start_edit(db, session, channel)
        # Buttons only work in REVIEW/IDLE; anything else falls through to media/text.

        if state == WhatsAppState.AWAITING_PHOTO:
            out = self._state_awaiting_photo(db, user, profile, session, image_bytes)
        elif state == WhatsAppState.AWAITING_VOICE:
            out = self._state_awaiting_voice(db, user, profile, session, voice_bytes, text, language_hint)
        elif state == WhatsAppState.PROCESSING:
            # Re-entry while a previous exchange is still processing — acknowledge politely.
            out = [mc.text_message("Still working on your product… one moment. ⏳")]
        elif state == WhatsAppState.REVIEW:
            # Stray media/text while waiting for a button — steer back gently.
            out = [mc.quick_reply_message(
                "Please choose: publish this listing, or edit it first?",
                [(BTN_PUBLISH, "✅ Yes, publish"), (BTN_EDIT, "✏️ Edit")],
            )]
        elif state == WhatsAppState.EDITING:
            out = self._state_editing(db, user, profile, session, text, voice_bytes, language_hint)
        elif state == WhatsAppState.IDLE:
            # Ready for the artisan's next product.
            if image_bytes:
                out = self._attach_photo(db, user, profile, session, image_bytes)
                out.append(mc.text_message(ASK_VOICE))
                session.current_state = WhatsAppState.AWAITING_VOICE
            else:
                out = [mc.text_message(GREETING)]
                session.current_state = WhatsAppState.AWAITING_PHOTO

        session.last_message_at = datetime.now(timezone.utc)
        sent = channel.send(session.phone, out) if out else []
        return {"messages": sent, "state": session.current_state}

    # ---------------------------------------------------------------- states

    def _state_awaiting_photo(self, db: Session, user: User, profile: ArtisanProfile,
                              session: WhatsAppSession, image_bytes: Optional[bytes]) -> list[mc.OutboundMessage]:
        if not image_bytes:
            return [mc.text_message("Please send a *photo* of the product to start 📸")]
        out = self._attach_photo(db, user, profile, session, image_bytes)
        out.append(mc.text_message(ASK_VOICE))
        session.current_state = WhatsAppState.AWAITING_VOICE
        return out

    def _attach_photo(self, db: Session, user: User, profile: ArtisanProfile,
                      session: WhatsAppSession, image_bytes: bytes) -> list[mc.OutboundMessage]:
        """Create the draft listing and attach the photo (same service path the
        main app uses — POST /api/v1/products + /{id}/images logic)."""
        mime = sniff_image_mime(image_bytes)
        if mime not in ("image/jpeg", "image/png", "image/webp"):
            return [mc.text_message("That doesn't look like a photo. Please send a JPG, PNG or WebP image 📷")]
        from app.services.media_service import store_upload

        try:
            stored = store_upload(image_bytes, prefix="wa_product")
        except ValidationFailedError as e:
            return [mc.text_message(str(e))]
        product = product_service.create_product(db, user=user, title="")  # draft
        img = product_service.add_image(db, product, url=stored["url"], mime=stored["mime"],
                                        size=stored["size"])
        session.draft_listing_id = product.id
        session.current_state = WhatsAppState.AWAITING_VOICE
        return [mc.image_message(stored["url"], caption="Photo received ✅")]

    def _state_awaiting_voice(self, db: Session, user: User, profile: ArtisanProfile,
                              session: WhatsAppSession, voice_bytes: Optional[bytes],
                              text: Optional[str], language_hint: Optional[str]) -> list[mc.OutboundMessage]:
        if not voice_bytes and not text:
            return [mc.text_message("Please send a *voice note* (or type a description) 🎙️")]
        session.current_state = WhatsAppState.PROCESSING
        session.last_message_at = datetime.now(timezone.utc)
        try:
            review_msgs = self._run_pipeline(db, user, profile, session, voice_bytes, text, language_hint)
        except ValidationFailedError as e:
            session.current_state = WhatsAppState.AWAITING_VOICE
            return [mc.text_message(f"⚠️ {e}")]
        session.current_state = WhatsAppState.REVIEW
        return [mc.text_message(PROCESSING_NOTE), *review_msgs]

    def _run_pipeline(self, db: Session, user: User, profile: ArtisanProfile,
                      session: WhatsAppSession, voice_bytes: Optional[bytes],
                      text: Optional[str], language_hint: Optional[str]) -> list[mc.OutboundMessage]:
        """The shared AI pipeline — identical services the main app calls. No AI
        logic lives here: enhance → transcribe → extract → generate → price."""
        product = product_service.get_owned_product(db, session.draft_listing_id, user)
        enforce("ai", user.id)  # shared AI rate limit, same as the app's AI endpoints

        # 1) enhance-photo (shared demo vision provider via the pipeline's vision path)
        primary = next((i for i in product.images if i.is_primary), product.images[0] if product.images else None)
        enhanced_url = None
        if primary is not None:
            try:
                from app.ai.providers import get_vision

                data = self._read_media(primary.original_url)
                if data:
                    result = get_vision().enhance(data)
                    enhanced_url = result.enhanced_path
                    # Set on the primary row (same structure the app wizard produces).
                    primary.enhanced_url = enhanced_url
                    db.flush()
            except Exception:
                enhanced_url = None  # enhancement is best-effort; original stays

        # 2) transcribe-voice (+ translate) — pipeline.process_voice
        if text:
            voice = pipeline.process_voice(db, audio_bytes=None, text=text, language_hint=language_hint,
                                           user_id=user.id, product_id=product.id)
        elif voice_bytes:
            voice = pipeline.process_voice(db, audio_bytes=voice_bytes, text=None, language_hint=language_hint,
                                           user_id=user.id, product_id=product.id)
        else:  # unreachable: callers validate
            raise ValidationFailedError("Send a voice note describing your product.")

        # 3) generate-listing — pipeline.extract_attributes + generate_catalogue
        extracted = pipeline.extract_attributes(db, transcript_en=voice["translated"],
                                                transcript_original=voice["transcript"], user_id=user.id)
        region = ", ".join(filter(None, [profile.city or profile.village, profile.state])) or ""
        catalogue = pipeline.generate_catalogue(db, extracted=extracted, artisan_name=profile.display_name,
                                                region=region, user_id=user.id, product_id=product.id)

        # Persist structured attributes + copy onto the product (same as the app wizard).
        product_service.set_attributes(db, product, extracted)
        self._apply_extracted_fields(product, extracted)
        product.title = (catalogue.get("title") or product.title or "Handmade product")[:250]
        product.short_description = catalogue.get("short_description")
        product.description = catalogue.get("description")
        product.keywords = catalogue.get("keywords")
        product.ai_catalogue_generated = True
        product.lifecycle = ProductLifecycle.REVIEW_REQUIRED
        if isinstance(extracted.get("category"), dict):
            product.category_id = product_service.resolve_category(db, extracted["category"].get("value"))
        db.flush()

        session.last_transcript_en = voice["translated"]
        session.last_transcript_original = voice["transcript"]

        # 4) price-suggestion — the shared pricing service with honest inputs.
        material = extracted.get("material", {}).get("value") if isinstance(extracted.get("material"), dict) else None
        days = extracted.get("production_days", {}).get("value") if isinstance(extracted.get("production_days"), dict) else None
        category = extracted.get("category", {}).get("value") if isinstance(extracted.get("category"), dict) else None
        inputs = PricingInputs(
            material_cost=120.0, labour_cost=max(80.0, 25.0 * float(days or 3)),
            category_hint=category, production_days=int(days) if days else None,
            product_id=product.id,
        )
        rec = pricing_service.recommend(db, user=user, inputs=inputs)
        price = Decimal(str(round(rec.suggested_price, 2)))
        product.price = price
        db.flush()
        session.suggested_price = f"₹{price:,.0f}"

        return self._review_messages(product, catalogue, rec, enhanced_url)

    def _review_messages(self, product: Product, catalogue: dict, rec, enhanced_url: Optional[str]) -> list[mc.OutboundMessage]:
        lo, hi = round(rec.market_low), round(rec.market_high)
        body = (
            f"*{catalogue.get('title', '')}*\n\n{catalogue.get('short_description', '')}\n\n"
            f"💰 Suggested price: *₹{rec.suggested_price:,.0f}* "
            f"(market band ₹{lo:,}–₹{hi:,})\n\n"
            "Reply below to publish or change anything."
        )
        msgs: list[mc.OutboundMessage] = []
        if enhanced_url:
            msgs.append(mc.image_message(enhanced_url, caption="Enhanced photo ✨"))
        elif product.images:
            msgs.append(mc.image_message(product.images[0].original_url))
        msgs.append(mc.quick_reply_message(
            body,
            [(BTN_PUBLISH, "✅ Yes, publish"), (BTN_EDIT, "✏️ Edit")],
            ai_tag=True,
        ))
        return msgs

    def _publish(self, db: Session, user: User, profile: ArtisanProfile,
                 session: WhatsAppSession, channel: mc.IMessagingChannel) -> dict:
        product = product_service.get_owned_product(db, session.draft_listing_id, user)
        try:
            product_service.publish(db, product)
        except ValidationFailedError as e:
            return {"messages": channel.send(session.phone, [mc.text_message(f"⚠️ {e}")]),
                    "state": session.current_state}
        from app.core.events import bus, PRODUCT_PUBLISHED
        from app.services.analytics_service import analytics_service

        bus.publish(PRODUCT_PUBLISHED, {"product_id": product.id})
        analytics_service.track(db, event_type="PRODUCT_PUBLISHED", actor=user,
                                entity_type="product", entity_id=product.id)
        session.published_product_id = product.id
        session.current_state = WhatsAppState.IDLE
        session.last_message_at = datetime.now(timezone.utc)
        link = PUBLISHED_LINK.format(pid=product.id)
        msgs = [
            mc.text_message(
                f"🎉 Published! Your product is now live on KARVANTANA.\n\n"
                f"View it here: {link}\n\n"
                "Buyers can find it in the marketplace immediately. Send the next "
                "product photo whenever you're ready — I'm here."
            ),
        ]
        return {"messages": channel.send(session.phone, msgs), "state": session.current_state}

    def _start_edit(self, db: Session, session: WhatsAppSession, channel: mc.IMessagingChannel) -> dict:
        session.current_state = WhatsAppState.EDITING
        session.last_message_at = datetime.now(timezone.utc)
        return {"messages": channel.send(session.phone, [mc.text_message(EDIT_PROMPT)]),
                "state": session.current_state}

    # Extracted field → product column (with the column's length limit), the same
    # mapping the main app's ProductWizard applies after AI extraction. Filling
    # these columns is what makes WhatsApp listings identical to app listings in
    # marketplace filters and the B2B directory.
    _COLUMN_MAP = {
        "material": 200, "technique": 120, "colour": 60, "usage": 300,
    }

    def _apply_extracted_fields(self, product: Product, extracted: dict) -> None:
        for key, limit in self._COLUMN_MAP.items():
            v = extracted.get(key)
            if isinstance(v, dict) and v.get("value") not in (None, ""):
                setattr(product, key, str(v["value"])[:limit])
        days = extracted.get("production_days")
        if isinstance(days, dict) and isinstance(days.get("value"), int):
            product.production_days = days["value"]
            # A stated production time means the piece is made to order — the same
            # rule the app wizard applies; it also keeps the listing orderable
            # (MADE_TO_ORDER products are not stock-limited).
            if product.inventory_mode == "STOCK" and product.stock_quantity == 0:
                product.inventory_mode = "MADE_TO_ORDER"

    def _correction_overrides(self, db: Session, user: User, correction_en: str) -> dict:
        """Fields the artisan explicitly corrects → ARTISAN_INPUT at confidence 1.0.
        This reuses the SAME extract_attributes pipeline (no new AI logic) and the
        app's own precedence rule: artisan corrections outrank AI-derived values
        (product_service.set_attributes never downgrades ARTISAN_INPUT)."""
        cleaned = self._NEGATION.sub("", correction_en)
        overrides = pipeline.extract_attributes(db, transcript_en=cleaned,
                                                transcript_original=cleaned, user_id=user.id)
        return {k: {"value": v["value"], "confidence": 1.0, "source": "ARTISAN_INPUT"}
                for k, v in overrides.items() if isinstance(v, dict)}

    def _state_editing(self, db: Session, user: User, profile: ArtisanProfile,
                       session: WhatsAppSession, text: Optional[str],
                       voice_bytes: Optional[bytes], language_hint: Optional[str]) -> list[mc.OutboundMessage]:
        if not text and not voice_bytes:
            return [mc.text_message("Tell me the change as a voice note or text 🎙️✍️")]
        # Append the correction to the last transcript → genuinely regenerate.
        session.current_state = WhatsAppState.PROCESSING
        session.last_message_at = datetime.now(timezone.utc)
        try:
            if voice_bytes or text:
                if text:
                    voice = pipeline.process_voice(db, audio_bytes=None, text=text,
                                                   language_hint=language_hint or "en",
                                                   user_id=user.id)
                else:
                    voice = pipeline.process_voice(db, audio_bytes=voice_bytes, text=None,
                                                   language_hint=language_hint, user_id=user.id)
                correction_en = voice["translated"]
                combined_en = f"{session.last_transcript_en or ''}\nCorrection: {correction_en}".strip()
                combined_original = f"{session.last_transcript_original or ''}\n{voice['transcript']}".strip()
            else:
                correction_en = ""
                combined_en = session.last_transcript_en or ""
                combined_original = session.last_transcript_original or ""
            session.last_transcript_en = combined_en
            session.last_transcript_original = combined_original

            product = product_service.get_owned_product(db, session.draft_listing_id, user)
            extracted = pipeline.extract_attributes(db, transcript_en=combined_en,
                                                    transcript_original=combined_original, user_id=user.id)
            # Artisan-stated corrections outrank anything re-derived from the old
            # transcript — the same ARTISAN_INPUT-wins rule the app applies.
            if correction_en:
                extracted = {**extracted, **self._correction_overrides(db, user, correction_en)}
            region = ", ".join(filter(None, [profile.city or profile.village, profile.state])) or ""
            catalogue = pipeline.generate_catalogue(db, extracted=extracted, artisan_name=profile.display_name,
                                                    region=region, user_id=user.id, product_id=product.id)
            product_service.set_attributes(db, product, extracted)
            self._apply_extracted_fields(product, extracted)
            product.title = (catalogue.get("title") or product.title)[:250]
            product.short_description = catalogue.get("short_description")
            product.description = catalogue.get("description")
            product.keywords = catalogue.get("keywords")
            db.flush()

            material = extracted.get("material", {}).get("value") if isinstance(extracted.get("material"), dict) else None
            days = extracted.get("production_days", {}).get("value") if isinstance(extracted.get("production_days"), dict) else None
            category = extracted.get("category", {}).get("value") if isinstance(extracted.get("category"), dict) else None
            inputs = PricingInputs(material_cost=120.0, labour_cost=max(80.0, 25.0 * float(days or 3)),
                                   category_hint=category, production_days=int(days) if days else None,
                                   product_id=product.id)
            rec = pricing_service.recommend(db, user=user, inputs=inputs)
            product.price = Decimal(str(round(rec.suggested_price, 2)))
            db.flush()
            session.suggested_price = f"₹{product.price:,.0f}"
        except ValidationFailedError as e:
            session.current_state = WhatsAppState.EDITING
            return [mc.text_message(f"⚠️ {e}")]
        session.current_state = WhatsAppState.REVIEW
        primary = next((i for i in product.images if i.enhanced_url), None) or \
            next((i for i in product.images if i.is_primary), product.images[0] if product.images else None)
        msgs = [mc.text_message("Updated ✨ Here's the new version:")]
        if primary is not None:
            msgs.append(mc.image_message(primary.enhanced_url or primary.original_url))
        msgs.append(mc.quick_reply_message(
            f"*{product.title}*\n\n{product.short_description}\n\n💰 Suggested price: ₹{product.price:,.0f}\n\n"
            "Publish this, or keep editing?",
            [(BTN_PUBLISH, "✅ Yes, publish"), (BTN_EDIT, "✏️ Edit")],
            ai_tag=True,
        ))
        return msgs

    # ------------------------------------------------------------------ util

    def _profile(self, db: Session, user: User) -> ArtisanProfile:
        profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
        if profile is None:
            raise ValidationFailedError("Complete artisan onboarding before using the WhatsApp assistant.")
        return profile

    def _read_media(self, url: str) -> Optional[bytes]:
        import os

        from app.core.config import get_settings

        base = os.path.abspath(get_settings().MEDIA_DIR)
        path = os.path.abspath(os.path.join(base, os.path.basename(url)))
        if not path.startswith(base) or not os.path.exists(path):
            return None
        with open(path, "rb") as fh:
            return fh.read()


whatsapp_bot = WhatsAppBot()
