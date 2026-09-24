"""WhatsApp webhook + thread endpoints (/api/v1/whatsapp).

The prototype's simulator calls these routes directly. The webhook accepts TWO
request shapes:

  1. multipart/form-data (the simulator: text / button / attached photo / voice
     note in one call), and
  2. the real WhatsApp Cloud API webhook JSON envelope (entry[].changes[].value.
     messages[]) — so swapping in the real integration later is a transport
     change, not a state-machine change. Real media (links) arrive as URLs;
     they are fetched and stored through the same media service.

Auth: the artisan signs in with the normal session; their on-file phone number
(added on the profile) identifies the WhatsApp thread. There is no separate
bot account — the WhatsApp front door drives the SAME pipeline as the app.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ValidationFailedError
from app.models.user import User
from app.models.whatsapp import WhatsAppMessage, WhatsAppSession
from app.security.dependencies import get_current_user
from app.services import messaging_channel as mc
from app.services.whatsapp_bot import whatsapp_bot
from app.services.whatsapp_service import subscribe_all

logger = logging.getLogger("karvantana.whatsapp")
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _phone_of(user: User) -> Optional[str]:
    return (user.phone or "").strip() or None


@router.post("/phone", summary="Attach a phone number to my account (WhatsApp thread id)")
def set_phone(payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    raw = str(payload.get("phone", ""))
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) < 10:
        raise ValidationFailedError("Enter a valid mobile number.")
    phone = digits[-10:]
    user.phone = phone
    db.flush()
    session = whatsapp_bot.get_or_create_session(db, user, phone)
    channel = mc.get_channel(db)
    messages = whatsapp_bot.ensure_greeting(db, session, channel)
    return {"phone": phone, "state": session.current_state, "messages": messages}


@router.get("/thread", summary="Replay my WhatsApp thread (persisted messages)")
def thread(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    phone = _phone_of(user)
    session = None
    if phone:
        session = db.query(WhatsAppSession).filter(WhatsAppSession.phone == phone).first()
    if session is None:
        return {"phone": None, "state": None, "messages": []}
    rows = (
        db.query(WhatsAppMessage)
        .filter(WhatsAppMessage.phone == phone)
        .order_by(WhatsAppMessage.created_at.asc(), WhatsAppMessage.id.asc())
        .limit(500)
        .all()
    )
    return {
        "phone": phone,
        "state": session.current_state,
        "draft_listing_id": session.draft_listing_id,
        "published_product_id": session.published_product_id,
        "messages": [
            {"id": r.id, "direction": r.direction, "kind": r.kind, "payload": r.payload,
             "created_at": r.created_at.isoformat()}
            for r in rows
        ],
    }


@router.post("/webhook", summary="Inbound WhatsApp message (simulator now, Cloud API later)")
async def webhook(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    text: Optional[str] = Form(None),
    button_id: Optional[str] = Form(None),
    language_hint: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
):
    # (AI calls inside the state machine enforce their own shared "ai" rate limit;
    #  the webhook itself is auth-gated and light.)
    phone = _phone_of(user)
    if not phone:
        raise ValidationFailedError("Add your WhatsApp number first (profile → WhatsApp).")

    # Real Cloud API envelope passthrough (no media files, JSON body with entry[])
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        envelope = await request.json()
        return _handle_cloud_envelope(db, user, phone, envelope)

    image_bytes = await image.read() if image is not None and image.filename else None
    voice_bytes = await audio.read() if audio is not None and audio.filename else None
    if voice_bytes and len(voice_bytes) > 8 * 1024 * 1024:
        raise ValidationFailedError("Voice notes can be up to 8 MB.")
    if image_bytes and len(image_bytes) > 10 * 1024 * 1024:
        raise ValidationFailedError("Photos can be up to 10 MB.")

    # Persist the inbound message so thread replay is faithful.
    if image_bytes:
        _persist_inbound(db, phone, "image", {"note": "photo attachment"})
    elif voice_bytes:
        _persist_inbound(db, phone, "voice", {"duration_hint": len(voice_bytes) // 8000 or 1})
    elif button_id:
        _persist_inbound(db, phone, "interactive", {"button_id": button_id})
    elif text:
        _persist_inbound(db, phone, "text", {"body": text})

    return _drive(db, user, phone, text=text, button_id=button_id, language_hint=language_hint,
                  image_bytes=image_bytes, voice_bytes=voice_bytes)


def _drive(db: Session, user: User, phone: str, *, text=None, button_id=None,
           language_hint=None, image_bytes=None, voice_bytes=None) -> dict:
    session = whatsapp_bot.get_or_create_session(db, user, phone)
    channel = mc.get_channel(db)
    greeting = whatsapp_bot.ensure_greeting(db, session, channel)
    try:
        result = whatsapp_bot.handle_inbound(
            db, user, session, channel,
            text=text, image_bytes=image_bytes, voice_bytes=voice_bytes,
            button_id=button_id, language_hint=language_hint,
        )
    except ValidationFailedError as e:
        result = {"messages": channel.send(phone, [mc.text_message(f"⚠️ {e}")]),
                  "state": session.current_state}
    result["greeting"] = greeting
    return result


def _persist_inbound(db: Session, phone: str, kind: str, payload: dict) -> None:
    db.add(WhatsAppMessage(phone=phone, direction="IN", message_id=mc.new_outbound_id(),
                           kind=kind, payload=payload))
    db.flush()


def _handle_cloud_envelope(db: Session, user: User, phone: str, envelope: dict) -> dict:
    """Minimal mapping of the real WhatsApp Cloud API webhook envelope onto the
    same state machine. Text + interactive buttons are supported natively; media
    messages arrive as links (the real integration resolves media ids via the
    Cloud API media endpoint, then reuses the same store_upload path)."""
    all_messages: list[dict] = []
    state = None
    for entry in envelope.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):
                kind = msg.get("type", "text")
                text = button_id = None
                image_bytes = voice_bytes = None
                inbound_payload: dict = {"kind": kind}
                if kind == "text":
                    text = (msg.get("text") or {}).get("body")
                    inbound_payload["body"] = text
                elif kind == "interactive":
                    reply = (msg.get("interactive") or {}).get("button_reply") or {}
                    button_id = reply.get("id")
                    inbound_payload["button_id"] = button_id
                elif kind == "image":
                    link = (msg.get("image") or {}).get("link")
                    image_bytes = _fetch_media(link)
                    inbound_payload["media_link"] = link
                elif kind == "audio" or kind == "voice":
                    link = (msg.get("audio") or msg.get("voice") or {}).get("link")
                    voice_bytes = _fetch_media(link)
                    inbound_payload["media_link"] = link
                _persist_inbound(db, phone, kind, inbound_payload)
                result = _drive(db, user, phone, text=text, button_id=button_id,
                                image_bytes=image_bytes, voice_bytes=voice_bytes)
                all_messages.extend(result.get("messages", []))
                state = result.get("state")
    return {"messages": all_messages, "state": state}


def _fetch_media(link: str) -> Optional[bytes]:
    """Fetch a media link into bytes (Cloud API path). Local /media URLs are
    served from disk; anything else requires an outbound HTTP call."""
    if not link:
        return None
    import os

    from app.core.config import get_settings

    if link.startswith("/media/"):
        base = os.path.abspath(get_settings().MEDIA_DIR)
        path = os.path.abspath(os.path.join(base, os.path.basename(link)))
        if path.startswith(base) and os.path.exists(path):
            with open(path, "rb") as fh:
                return fh.read()
        return None
    try:
        import httpx

        resp = httpx.get(link, timeout=10.0, follow_redirects=True)
        return resp.content if resp.status_code == 200 else None
    except Exception:
        logger.warning("Could not fetch WhatsApp media link: %s", link)
        return None


# Install the notification bridge exactly once at import time (same module the
# router is registered from, so it is always active when the app runs).
subscribe_all()
