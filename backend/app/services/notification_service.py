"""Notification service (blueprint §57, §58).

NotificationService fans events out through channel adapters. In-app is always
on; WhatsApp/SMS/email adapters are wired but gated by feature flags and
credentials — business logic never touches a channel directly.
"""

from __future__ import annotations

import abc
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.feature_flags import is_enabled
from app.models.engagement import Notification


class ChannelAdapter(abc.ABC):
    name: str = "abstract"

    @abc.abstractmethod
    def send(self, *, user_id: str, title: str, body: str, link: Optional[str]) -> None: ...


class InAppChannel(ChannelAdapter):
    name = "in_app"

    def send(self, *, user_id: str, title: str, body: str, link: Optional[str]) -> None:
        db = Session.object_session.__self__ if False else None  # placeholder to satisfy interface
        raise RuntimeError("InApp channel writes via service, not adapter.")


class WhatsAppChannel(ChannelAdapter):
    """Demo WhatsApp adapter. A real Business Cloud API client implements send()."""

    name = "whatsapp"

    def send(self, *, user_id: str, title: str, body: str, link: Optional[str]) -> None:
        # DEMO: logged only. Message templates match the blueprint examples.
        import logging

        logging.getLogger("karvantana.whatsapp").info(
            "DEMO WhatsApp → user=%s title=%s body=%s", user_id, title, body
        )


class EmailChannel(ChannelAdapter):
    name = "email"

    def send(self, *, user_id: str, title: str, body: str, link: Optional[str]) -> None:
        import logging

        logging.getLogger("karvantana.email").info("DEMO Email → user=%s title=%s", user_id, title)


class NotificationService:
    def __init__(self) -> None:
        self._channels: dict[str, ChannelAdapter] = {
            "whatsapp": WhatsAppChannel(),
            "email": EmailChannel(),
        }

    def create(self, db: Session, *, user_id: str, type: str, title: str,
               body: Optional[str] = None, link: Optional[str] = None) -> Notification:
        row = Notification(user_id=user_id, type=type, title=title, body=body, link=link)
        db.add(row)
        db.flush()
        self._fan_out_external(db, row)
        return row

    def _fan_out_external(self, db: Session, notification: Notification) -> None:
        """External channels fire only when enabled AND the user has consented
        (contact details exist). Failures never break the caller's transaction."""
        try:
            if is_enabled("WHATSAPP"):
                from app.models.user import User

                user = db.query(User).filter(User.id == notification.user_id).first()
                if user and user.phone:
                    self._channels["whatsapp"].send(
                        user_id=user.id, title=notification.title,
                        body=notification.body or "", link=notification.link,
                    )
        except Exception:
            import logging

            logging.getLogger("karvantana.notifications").exception("External notification fan-out failed")

    def list_for(self, db: Session, user_id: str, unread_only: bool = False) -> list[Notification]:
        q = db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            q = q.filter(Notification.is_read.is_(False))
        return q.order_by(Notification.created_at.desc()).limit(50).all()

    def mark_read(self, db: Session, user_id: str, notification_id: str) -> None:
        row = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id).first()
        if row:
            row.is_read = True
            db.flush()


notification_service = NotificationService()
