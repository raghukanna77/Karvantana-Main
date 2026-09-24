"""IMessagingChannel — the only seam between the bot's brain and its delivery.

`WhatsAppBot` (state machine) decides WHAT to say and returns a list of
structured `OutboundMessage` objects (text / image / voice-note / quick-reply
buttons, mirroring the WhatsApp Cloud API message types). A channel decides HOW
those objects reach the artisan:

  • `SimulatorChannel` (prototype): messages ride on the HTTP webhook response,
    and every message is persisted to `whatsapp_messages` so the thread can be
    replayed in the chat simulator.
  • `WhatsAppCloudChannel` (drop-in later): implements the same send() against
    the real Cloud API — POST /{phone_number_id}/messages with the matching
    message-type payloads. Swapping channels requires ZERO changes to the
    state machine.

Outbound message shapes intentionally mirror WhatsApp Cloud API content types:
  text → {"type": "text", "text": {"body", "preview_url"}}
  image → {"type": "image", "image": {"link"}}
  voice → {"type": "audio", "audio": {"link"}}
  interactive quick-reply → {"type": "interactive", "interactive": {"type": "button",
                             "body": {"text"}, "action": {"buttons": [{id, title}]}}}
"""

from __future__ import annotations

import abc
from datetime import datetime, timezone
from typing import Any, Optional


def new_outbound_id() -> str:
    import uuid

    return str(uuid.uuid4())


class OutboundMessage:
    """One outgoing bot bubble. Built by the state machine, delivered by a channel."""

    def __init__(self, kind: str, payload: dict[str, Any]):
        self.kind = kind  # "text" | "image" | "voice" | "interactive"
        self.payload = payload
        self.id = new_outbound_id()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "payload": self.payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def text_message(body: str, ai_tag: bool = False) -> OutboundMessage:
    return OutboundMessage("text", {"body": body, "ai_tag": ai_tag})


def image_message(link: str, caption: str = "") -> OutboundMessage:
    return OutboundMessage("image", {"link": link, "caption": caption})


def voice_message(link: str, duration_seconds: int = 0) -> OutboundMessage:
    return OutboundMessage("voice", {"link": link, "duration_seconds": duration_seconds})


def quick_reply_message(body: str, buttons: list[tuple[str, str]], ai_tag: bool = False) -> OutboundMessage:
    """buttons: [(button_id, label), …] — rendered as WhatsApp pill buttons."""
    return OutboundMessage(
        "interactive",
        {
            "body": body,
            "buttons": [{"id": bid, "title": title} for bid, title in buttons],
            "ai_tag": ai_tag,
        },
    )


class IMessagingChannel(abc.ABC):
    """Delivery seam. The bot never knows how messages physically travel."""

    name: str = "abstract"

    @abc.abstractmethod
    def send(self, phone: str, messages: list[OutboundMessage]) -> list[dict]: ...


class SimulatorChannel(IMessagingChannel):
    """Prototype channel: persists to whatsapp_messages; the webhook response
    carries the same payload so the chat simulator renders it instantly. A real
    WhatsApp Cloud API key later → implement WhatsAppCloudChannel(IMessagingChannel)
    and swap the factory below; the state machine does not change."""

    name = "whatsapp_simulator"

    def send(self, phone: str, messages: list[OutboundMessage]) -> list[dict]:
        from app.core.database import SessionLocal
        from app.models.whatsapp import WhatsAppMessage

        rendered: list[dict] = []
        db = SessionLocal()
        try:
            for msg in messages:
                data = msg.to_dict()
                row = WhatsAppMessage(phone=phone, direction="OUT", message_id=data["id"],
                                      kind=data["kind"], payload=data["payload"])
                db.add(row)
                rendered.append(data)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        return rendered


class SimulatorChannelInSession(SimulatorChannel):
    """Variant used inside an open request transaction (tests, webhook) — reuses
    the caller's session instead of opening a second one."""

    name = "whatsapp_simulator_in_session"

    def __init__(self, db) -> None:
        self._db = db

    def send(self, phone: str, messages: list[OutboundMessage]) -> list[dict]:
        from app.models.whatsapp import WhatsAppMessage

        rendered = []
        for msg in messages:
            data = msg.to_dict()
            self._db.add(WhatsAppMessage(phone=phone, direction="OUT", message_id=data["id"],
                                         kind=data["kind"], payload=data["payload"]))
            rendered.append(data)
        self._db.flush()
        return rendered


def get_channel(db=None) -> IMessagingChannel:
    """Channel factory — the single place a real integration swaps in."""
    if db is not None:
        return SimulatorChannelInSession(db)
    return SimulatorChannel()
