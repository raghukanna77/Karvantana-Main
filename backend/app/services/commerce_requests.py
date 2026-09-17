"""Bulk (B2B) and custom request workflows with AI requirement parsing,
artisan matching, quotes and acceptance → order (blueprint §20, §25, §26)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import time
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.providers import get_llm
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationFailedError
from app.core.events import bus, BULK_REQUEST_CREATED, CUSTOM_REQUEST_CREATED, QUOTE_CREATED
from app.models.product import Product
from app.models.commerce import BulkRequest, CustomRequest, Quote, QuoteStatus
from app.models.profile import ArtisanProfile
from app.services.notification_service import notification_service
from app.services import order_service as order_svc


class MatchingService:
    """Hybrid matching: structured rules + text relevance + capacity/lead-time.
    Returns scored candidates with explainable match reasons (blueprint §80).
    Filters relax progressively — a tight budget narrows results instead of
    producing an empty page (blueprint §21: business constraints, not hard walls)."""

    def match_products(self, db: Session, parsed: dict, limit: int = 6) -> list[dict]:
        relaxations = ((False, None), ("budget", "Closest match — slightly outside the stated budget"),
                       ("category", "Broad match from the catalogue"))
        for relaxed, tag in relaxations:
            effective = dict(parsed)
            if relaxed in ("budget", "category"):
                effective["max_unit_price"] = None
            if relaxed == "category":
                effective["category"] = None
            candidates = self._candidates(db, effective)
            scored = self._score(candidates, effective)
            if scored:
                if tag:
                    for s in scored:
                        s["reasons"].append(tag)
                return scored[:limit]
        return []

    def _candidates(self, db: Session, parsed: dict) -> list[Product]:
        query = db.query(Product).filter(Product.lifecycle == "PUBLISHED")
        category = parsed.get("category")
        if category:
            lowered = str(category).lower()
            query = query.filter(
                Product.title.ilike(f"%{lowered}%") | Product.keywords.ilike(f"%{lowered}%")
                | Product.material.ilike(f"%{lowered}%")
            )
        max_price = parsed.get("max_unit_price")
        if max_price:
            query = query.filter(Product.price <= Decimal(str(max_price)))
        if parsed.get("customization"):
            query = query.filter(Product.customization_available.is_(True))
        return query.limit(60).all()

    def _score(self, candidates: list[Product], parsed: dict) -> list[dict]:
        category = parsed.get("category")
        max_price = parsed.get("max_unit_price")
        scored: list[dict] = []
        for p in candidates:
            reasons, score = [], 0.0
            if category and str(category).lower() in ((p.title or "") + " " + (p.keywords or "") + " " + (p.material or "")).lower():
                reasons.append("Matches the requested product category")
                score += 0.35
            if max_price and float(p.price) <= float(max_price):
                reasons.append(f"Unit price ₹{float(p.price):,.0f} is within budget")
                score += 0.25
            if parsed.get("customization") and p.customization_available:
                reasons.append("Offers customization")
                score += 0.15
            if p.bulk_price and p.bulk_moq:
                reasons.append(f"Bulk price ₹{float(p.bulk_price):,.0f} for {p.bulk_moq}+ units")
                score += 0.15
            if parsed.get("quantity") and p.effective_stock >= parsed["quantity"]:
                reasons.append("Can fulfil the requested quantity")
                score += 0.10
            if score <= 0:
                score = 0.05
            scored.append({"product": p, "score": round(min(score, 1.0), 2), "reasons": reasons})
        scored.sort(key=lambda s: -s["score"])
        return scored

    def match_artisans_for_custom(self, db: Session, artisan_ids: list[str]) -> list[ArtisanProfile]:
        return db.query(ArtisanProfile).filter(ArtisanProfile.id.in_(artisan_ids)).all()


class RequestService:
    def __init__(self) -> None:
        self.matching = MatchingService()

    # ----------------------------------------------------------------- bulk

    def create_bulk_request(self, db: Session, *, buyer: User, title: str, description: str,
                            quantity: int, max_unit_price: Optional[Decimal],
                            required_by: Optional[datetime], customization_required: bool,
                            category_hint: Optional[str]) -> BulkRequest:
        if quantity < 2:
            raise ValidationFailedError("Bulk requests start at 2 units. For a single piece, place a normal order.")
        llm = get_llm()
        started = time.time()
        parsed = llm.parse_buyer_requirement(f"{title}. {description} quantity {quantity}"
                                             + (f" under ₹{max_unit_price}" if max_unit_price else "")
                                             + (f" within {required_by}" if required_by else ""))
        try:  # telemetry must never block commerce (blueprint §116)
            from app.models.ai import AIUsage

            db.add(AIUsage(task="requirement_parse", provider=llm.name,
                           model=getattr(llm, "model_name", llm.name),
                           latency_ms=int((time.time() - started) * 1000),
                           success=True, estimated_cost_usd=0.0))
        except Exception:
            pass
        req = BulkRequest(
            buyer_id=buyer.id,
            title=title[:200],
            description=description,
            category_hint=category_hint,
            quantity=quantity,
            max_unit_price=max_unit_price,
            required_by=required_by,
            customization_required=customization_required,
            parsed_requirements=parsed,
            status="OPEN",
        )
        db.add(req)
        db.flush()
        bus.publish(BULK_REQUEST_CREATED, {"request_id": req.id, "buyer_id": buyer.id})
        return req

    def bulk_matches(self, db: Session, request: BulkRequest, limit: int = 6) -> list[dict]:
        parsed = request.parsed_requirements or {}
        parsed = {**parsed, "quantity": request.quantity,
                  "max_unit_price": float(request.max_unit_price) if request.max_unit_price else parsed.get("max_unit_price")}
        matches = self.matching.match_products(db, parsed, limit=limit)
        out = []
        for m in matches:
            product = m["product"]
            out.append({
                "product_id": product.id,
                "title": product.title,
                "image_url": product.images[0].original_url if product.images else None,
                "price": float(product.price),
                "bulk_price": float(product.bulk_price) if product.bulk_price else None,
                "bulk_moq": product.bulk_moq,
                "artisan_id": product.artisan_id,
                "score": m["score"],
                "reasons": m["reasons"],
            })
        return out

    def create_quote(self, db: Session, *, artisan_user: User, request_type: str, request_id: str,
                     unit_price: Decimal, lead_time_days: int, note: Optional[str],
                     quantity: Optional[int] = None) -> Quote:
        profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == artisan_user.id).first()
        if profile is None:
            raise PermissionDeniedError("Complete artisan onboarding to quote.")
        if request_type == "BULK":
            req = db.query(BulkRequest).filter(BulkRequest.id == request_id).first()
            qty = quantity or (req.quantity if req else 1)
            if req is None:
                raise NotFoundError("Bulk request not found.")
        elif request_type == "CUSTOM":
            req = db.query(CustomRequest).filter(CustomRequest.id == request_id).first()
            if req is None:
                raise NotFoundError("Custom request not found.")
            qty = quantity or 1
        else:
            raise ValidationFailedError("Invalid request type.")
        if req.status in ("CLOSED", "ORDERED"):
            raise ConflictError("This request is closed.")
        total = (unit_price * qty).quantize(Decimal("0.01"))
        quote = Quote(
            request_type=request_type,
            request_id=request_id,
            artisan_id=profile.id,
            unit_price=unit_price,
            quantity=qty,
            total=total,
            lead_time_days=lead_time_days,
            note=(note or None),
            expires_at=datetime.utcnow() + timedelta(days=14),
        )
        db.add(quote)
        req.status = "QUOTING"
        db.flush()
        bus.publish(QUOTE_CREATED, {"quote_id": quote.id, "request_type": request_type})
        notification_service.create(db, user_id=req.buyer_id, type="QUOTE_RECEIVED",
                                    title="New quote received",
                                    body=f"₹{float(unit_price):,.0f}/unit × {qty} — see the full quote.",
                                    link=f"/{'b2b' if request_type == 'BULK' else 'buyer'}/requests")
        return quote

    def accept_quote(self, db: Session, *, buyer: User, quote_id: str, address: dict) -> dict:
        quote = db.query(Quote).filter(Quote.id == quote_id).first()
        if quote is None:
            raise NotFoundError("Quote not found.")
        if quote.status != QuoteStatus.PENDING:
            raise ConflictError("This quote is no longer open.")
        if quote.expires_at and quote.expires_at < datetime.utcnow():
            quote.status = QuoteStatus.EXPIRED
            raise ConflictError("This quote has expired.")

        if quote.request_type == "BULK":
            req = db.query(BulkRequest).filter(BulkRequest.id == quote.request_id).first()
        else:
            req = db.query(CustomRequest).filter(CustomRequest.id == quote.request_id).first()
        if req is None or req.buyer_id != buyer.id:
            raise PermissionDeniedError("You can only accept quotes on your own requests.")
        if req.status == "ORDERED":
            raise ConflictError("This request already has a confirmed order.")

        order = order_svc.order_service.create_order(
            db,
            buyer=buyer,
            items=[_quote_item(db, quote)],
            shipping_address=address,
            buyer_note=f"From {'bulk' if quote.request_type == 'BULK' else 'custom'} request",
        )
        order.is_bulk = quote.request_type == "BULK"
        order.related_request_id = req.id
        quote.status = QuoteStatus.ACCEPTED
        req.status = "ORDERED"
        db.flush()
        return {"order_id": order.id, "order_number": order.order_number, "total": float(order.total)}

    def list_for_buyer(self, db: Session, buyer_id: str) -> dict:
        bulk = db.query(BulkRequest).filter(BulkRequest.buyer_id == buyer_id).order_by(BulkRequest.created_at.desc()).all()
        custom = db.query(CustomRequest).filter(CustomRequest.buyer_id == buyer_id).order_by(CustomRequest.created_at.desc()).all()
        return {"bulk": bulk, "custom": custom}

    def list_for_artisan(self, db: Session, artisan_id: str) -> dict:
        custom = db.query(CustomRequest).filter(CustomRequest.artisan_id == artisan_id).order_by(CustomRequest.created_at.desc()).all()
        # Open bulk requests visible to the artisan (market linkage engine output)
        open_bulk = db.query(BulkRequest).filter(BulkRequest.status == "OPEN").order_by(BulkRequest.created_at.desc()).limit(20).all()
        return {"custom": custom, "open_bulk": open_bulk}


def _quote_item(db: Session, quote: Quote) -> dict:
    """Resolve a quote to an order line; for bulk/custom we need a product anchor.
    Quotes carry the matched product when the request came from matching; otherwise
    the artisan's latest published product in the category is used as the anchor."""
    from app.models.product import Product

    req = None
    if quote.request_type == "BULK":
        req = db.query(BulkRequest).filter(BulkRequest.id == quote.request_id).first()
    else:
        req = db.query(CustomRequest).filter(CustomRequest.id == quote.request_id).first()
    product = None
    if req is not None and getattr(req, "product_id", None):
        product = db.query(Product).filter(Product.id == req.product_id).first()
    if product is None and req is not None and hasattr(req, "category_hint") and req.category_hint:
        product = (
            db.query(Product)
            .filter(Product.artisan_id == quote.artisan_id, Product.lifecycle == "PUBLISHED")
            .order_by(Product.updated_at.desc())
            .first()
        )
    if product is None:
        product = (
            db.query(Product)
            .filter(Product.artisan_id == quote.artisan_id, Product.lifecycle == "PUBLISHED")
            .order_by(Product.updated_at.desc())
            .first()
        )
    if product is None:
        raise ValidationFailedError("Add a published product before quoting so buyers can order it.")
    # Quoted price is authoritative for the order line
    product_copy = product
    return {"product_id": product_copy.id, "quantity": quote.quantity, "_unit_price_override": float(quote.unit_price)}


request_service = RequestService()
