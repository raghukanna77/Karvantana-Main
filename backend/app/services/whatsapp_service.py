"""WhatsApp notification bridge — reuses the main app's notification flow.

The main app already creates Notification rows for every order / rating /
reorder event (notification_service.create is called by order_service,
review_service, payment_service…). This subscriber re-broadcasts those same
notifications into the WhatsApp thread of any artisan who has a WhatsApp
session — same content, same trigger points, delivered through the shared
IMessagingChannel. It never invents events of its own.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.models.whatsapp import WhatsAppSession
from app.services import messaging_channel as mc

logger = logging.getLogger("karvantana.whatsapp")

# Notification type → (icon, heading) for the chat rendering of the same event.
_CHAT_RENDER = {
    "ORDER_RECEIVED": ("🛍️", "New order received"),
    "PAYMENT_RECEIVED": ("💰", "Payment received"),
    "REVIEW_RECEIVED": ("⭐", "New review from a buyer"),
    "REORDER_CREATED": ("🔁", "A buyer ordered again"),
}


def _deliver_to_thread(db, user_id: str, notification) -> None:
    """Send an existing Notification into the user's WhatsApp thread (if any).

    Uses the CALLER's transaction on purpose: the chat message commits atomically
    with the event that caused it (and SQLite permits only one writer at a time).
    Failures are logged, never raised — a delivery problem must not break the
    order/review flow that triggered it."""
    from app.models.user import User

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return
    # The thread is keyed by the artisan's CURRENT phone on file (re-binding a
    # phone moves the thread with it).
    session = None
    if user.phone:
        session = db.query(WhatsAppSession).filter(WhatsAppSession.phone == user.phone).first()
    if session is None:
        return  # this artisan has never used the WhatsApp channel
    icon, heading = _CHAT_RENDER.get(notification.type, ("🔔", notification.title))
    body = f"{icon} *{heading}*\n{notification.body or ''}".strip()
    if notification.link:
        body += f"\n\nOpen: {notification.link}"
    channel = mc.get_channel(db)
    channel.send(session.phone, [mc.text_message(body)])
    session.last_message_at = datetime.now(timezone.utc)


def subscribe_all() -> None:
    """Register the bridge. Called once from create_app(); idempotent."""
    from app.services import notification_service as ns

    if getattr(ns.NotificationService.create, "_whatsapp_bridge", False):
        return
    original_create = ns.NotificationService.create

    def create_with_bridge(self, db, *, user_id, type, title, body=None, link=None):
        row = original_create(self, db, user_id=user_id, type=type, title=title, body=body, link=link)
        try:
            _deliver_to_thread(db, user_id, row)
        except Exception:
            logger.exception("WhatsApp notify bridge failed")
        return row

    create_with_bridge._whatsapp_bridge = True  # type: ignore[attr-defined]
    ns.NotificationService.create = create_with_bridge
    logger.info("WhatsApp notification bridge installed")
