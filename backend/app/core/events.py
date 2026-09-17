"""Domain event bus.

Services publish domain events; side-effect consumers (notifications, analytics,
worker jobs) subscribe. This keeps business logic decoupled from channels like
WhatsApp/email and makes event flow observable and testable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

logger = logging.getLogger("karvantana.events")


@dataclass
class DomainEvent:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    actor_id: Optional[str] = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


Subscriber = Callable[[DomainEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = {}

    def subscribe(self, event_name: str, handler: Subscriber) -> None:
        self._subscribers.setdefault(event_name, []).append(handler)

    def publish(self, event: "DomainEvent | str", payload: Optional[dict] = None,
                actor_id: Optional[str] = None) -> None:
        """Publish a DomainEvent, or (name, payload) as a convenience."""
        if isinstance(event, str):
            event = DomainEvent(name=event, payload=payload or {}, actor_id=actor_id)
        for handler in self._subscribers.get(event.name, []):
            try:
                handler(event)
            except Exception:  # subscriber failures must not break the main flow
                logger.exception("Event subscriber failed", extra={"event": event.name})


bus = EventBus()


# Canonical event names (mirrors the analytics event model)
ORDER_CREATED = "order.created"
ORDER_STATUS_CHANGED = "order.status_changed"
PAYMENT_CONFIRMED = "payment.confirmed"
PAYMENT_FAILED = "payment.failed"
BULK_REQUEST_CREATED = "bulk_request.created"
CUSTOM_REQUEST_CREATED = "custom_request.created"
QUOTE_CREATED = "quote.created"
REVIEW_CREATED = "review.created"
AI_CATALOGUE_GENERATED = "ai.catalogue_generated"
PRODUCT_PUBLISHED = "product.published"
ARTISAN_FOLLOWED = "artisan.followed"
REORDER_CREATED = "reorder.created"
