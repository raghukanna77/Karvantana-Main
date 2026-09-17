"""KARVANTANA Business Assistant (blueprint §31, §32).

Flow: question → intent → authorization → tool selection → data → explanation.
The LLM layer NEVER touches the database directly; tools return only rows the
caller is authorized to see. Answers quote tool output verbatim; when data is
missing the assistant says so — never invents numbers (hallucination guard).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

from sqlalchemy.orm import Session

from app.ai.providers import get_llm
from app.core.errors import PermissionDeniedError
from app.models.commerce import Order, OrderItem
from app.models.engagement import Review
from app.models.product import Product
from app.models.profile import ArtisanProfile
from app.models.user import User
from app.security.rbac import Role


@dataclass
class ToolResult:
    name: str
    data: dict
    summary: str


TOOL_SUMMARIES = {
    "top_products": "top products by units sold",
    "pending_orders": "orders waiting on the artisan",
    "monthly_sales": "this month's sales total",
    "sales_trend": "sales compared to last month",
    "needs_better_photos": "products with low image quality",
    "low_stock": "products running out of stock",
}


def _authorized_artisan(db: Session, user: User) -> ArtisanProfile:
    if user.role not in (Role.ARTISAN.value, Role.ADMIN.value):
        raise PermissionDeniedError("The business assistant is available for artisan accounts.")
    profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
    if profile is None:
        raise PermissionDeniedError("Complete artisan onboarding to use the assistant.")
    return profile


def _tool_top_products(db: Session, artisan_id: str, _args: dict) -> ToolResult:
    rows = (
        db.query(
            OrderItem.product_title_snapshot.label("title"),
            func_sum_qty := OrderItem.quantity,
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            OrderItem.artisan_id == artisan_id,
            Order.status.in_([OrderStatus_COMPLETED := "COMPLETED", "DELIVERED", "SHIPPED", "CONFIRMED", "PROCESSING", "IN_PRODUCTION", "READY_TO_SHIP"]),
        )
        .group_by(OrderItem.product_title_snapshot)
        .order_by(func_sum_qty.desc())
        .limit(5)
        .all()
    )
    data = [{"title": t, "units": int(q or 0)} for t, q in rows]
    if not data:
        summary = "No orders yet — once you receive orders, your best-selling products will appear here."
    else:
        summary = "Your best-selling products by units: " + ", ".join(f"{d['title']} ({d['units']})" for d in data)
    return ToolResult("top_products", {"products": data}, summary)


def _tool_pending_orders(db: Session, artisan_id: str, _args: dict) -> ToolResult:
    open_statuses = ("CONFIRMED", "PROCESSING", "IN_PRODUCTION", "READY_TO_SHIP")
    rows = (
        db.query(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .filter(OrderItem.artisan_id == artisan_id, Order.status.in_(open_statuses))
        .distinct()
        .order_by(Order.created_at.desc())
        .limit(10)
        .all()
    )
    data = [{"order_number": o.order_number, "status": OrderStatus_LABELS.get(o.status, o.status), "total": float(o.total)} for o in rows]
    summary = (
        f"You have {len(data)} order(s) in progress." if data
        else "No orders are waiting on you right now."
    )
    return ToolResult("pending_orders", {"orders": data}, summary)


def _tool_monthly_sales(db: Session, artisan_id: str, _args: dict) -> ToolResult:
    from datetime import datetime, timezone

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    paid_statuses = ("CONFIRMED", "PROCESSING", "IN_PRODUCTION", "READY_TO_SHIP", "SHIPPED", "DELIVERED", "COMPLETED")
    rows = (
        db.query(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            OrderItem.artisan_id == artisan_id,
            Order.status.in_(paid_statuses),
            Order.created_at >= month_start,
        )
        .all()
    )
    total = sum(float(i.line_total) for i in rows)
    orders = len({i.order_id for i in rows})
    summary = (
        f"Based on the available order data, your confirmed sales this month are ₹{total:,.0f} across {orders} order(s)."
        if rows else "No confirmed sales recorded yet this month."
    )
    return ToolResult("monthly_sales", {"total": total, "orders": orders}, summary)


def _tool_sales_trend(db: Session, artisan_id: str, _args: dict) -> ToolResult:
    from datetime import datetime, timedelta, timezone

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_start = (month_start - timedelta(days=1)).replace(day=1)
    paid = ("CONFIRMED", "PROCESSING", "IN_PRODUCTION", "READY_TO_SHIP", "SHIPPED", "DELIVERED", "COMPLETED")

    def revenue_since(start: datetime, end: datetime) -> float:
        rows = (
            db.query(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .filter(OrderItem.artisan_id == artisan_id, Order.status.in_(paid), Order.created_at >= start, Order.created_at < end)
            .all()
        )
        return sum(float(i.line_total) for i in rows)

    this_month = revenue_since(month_start, now)
    last_month = revenue_since(prev_start, month_start)
    if last_month == 0 and this_month == 0:
        return ToolResult("sales_trend", {"this_month": 0, "last_month": 0}, "No sales data for the last two months yet.")
    if last_month == 0:
        return ToolResult("sales_trend", {"this_month": this_month, "last_month": 0},
                          f"This month so far: ₹{this_month:,.0f}. No sales were recorded last month.")
    pct = (this_month - last_month) / last_month * 100
    direction = "up" if pct >= 0 else "down"
    return ToolResult("sales_trend", {"this_month": this_month, "last_month": last_month, "change_pct": round(pct, 1)},
                      f"Based on the available order data, sales are {direction} about {abs(pct):.0f}% compared to last month (₹{this_month:,.0f} vs ₹{last_month:,.0f}).")


def _tool_needs_better_photos(db: Session, artisan_id: str, _args: dict) -> ToolResult:
    products = (
        db.query(Product)
        .filter(Product.artisan_id == artisan_id, Product.lifecycle == "PUBLISHED")
        .all()
    )
    weak = []
    for p in products:
        primary = next((img for img in p.images if img.is_primary), p.images[0] if p.images else None)
        score = primary.quality_score if primary and primary.quality_score is not None else None
        if not p.images or (score is not None and score < 70):
            weak.append(p.title or "Untitled product")
    data = {"products": weak}
    summary = (
        "These products need better photos: " + ", ".join(weak) if weak
        else "All your product photos look good."
    )
    return ToolResult("needs_better_photos", data, summary)


def _tool_low_stock(db: Session, artisan_id: str, _args: dict) -> ToolResult:
    products = (
        db.query(Product)
        .filter(Product.artisan_id == artisan_id, Product.lifecycle == "PUBLISHED", Product.inventory_mode == "STOCK")
        .all()
    )
    low = [{"title": p.title or "Untitled", "stock": p.stock_quantity} for p in products if p.stock_quantity <= p.low_stock_threshold]
    summary = "Running low: " + ", ".join(f"{d['title']} ({d['stock']} left)" for d in low) if low else "Stock levels look healthy."
    return ToolResult("low_stock", {"products": low}, summary)


# ---- registry ---------------------------------------------------------------

def _labels() -> dict:
    from app.models.commerce import OrderStatus

    return OrderStatus.LABELS


OrderStatus_LABELS = _labels()
from sqlalchemy import func  # noqa: E402  (used inside tools)

TOOL_REGISTRY: dict[str, Callable[[Session, str, dict], ToolResult]] = {
    "top_products": _tool_top_products,
    "pending_orders": _tool_pending_orders,
    "monthly_sales": _tool_monthly_sales,
    "sales_trend": _tool_sales_trend,
    "needs_better_photos": _tool_needs_better_photos,
    "low_stock": _tool_low_stock,
}

INTENT_RULES: list[tuple[str, re.Pattern]] = [
    ("low_stock", re.compile(r"stock|inventory|running out", re.I)),
    ("needs_better_photos", re.compile(r"photo|image|picture", re.I)),
    ("pending_orders", re.compile(r"pending|open order|waiting|in progress|status of (my )?orders", re.I)),
    ("top_products", re.compile(r"selling well|best.?seller|top product|popular|what should i make more", re.I)),
    ("sales_trend", re.compile(r"why did .*fall|trend|compare|increased|decreased|last month|growth", re.I)),
    ("monthly_sales", re.compile(r"sales|revenue|earned|this month|how much", re.I)),
]


def detect_intent(question: str) -> str:
    for intent, rx in INTENT_RULES:
        if rx.search(question):
            return intent
    return "monthly_sales"


class AssistantService:
    def ask(self, db: Session, user: User, question: str) -> dict:
        profile = _authorized_artisan(db, user)
        intent = detect_intent(question)
        tool = TOOL_REGISTRY[intent]
        result = tool(db, profile.id, {})
        llm = get_llm()
        review_summary = None
        if intent in ("top_products", "sales_trend"):
            reviews = (
                db.query(Review).filter(Review.artisan_id == profile.id).order_by(Review.created_at.desc()).limit(20).all()
            )
            review_summary = llm.summarize_reviews([
                {"product_rating": r.product_rating, "text": r.text} for r in reviews
            ])
        answer_parts = [result.summary]
        if review_summary:
            answer_parts.append("Buyer feedback: " + review_summary)
        answer_parts.append(_next_action(intent, result))
        return {
            "intent": intent,
            "tool": result.name,
            "answer": " ".join(a for a in answer_parts if a),
            "data": result.data,
            "sources": [f"tool:{result.name}"],
        }


def _next_action(intent: str, result: ToolResult) -> Optional[str]:
    if intent == "top_products" and result.data.get("products"):
        return "Consider keeping 2–3 units of these ready and adding a related product buyers might want next."
    if intent == "needs_better_photos" and result.data.get("products"):
        return "Retake these photos in daylight near a window — better photos get more orders."
    if intent == "low_stock" and result.data.get("products"):
        return "Update stock or mark them as made-to-order so you don't miss orders."
    if intent == "pending_orders" and result.data.get("orders"):
        return "Tap each order to update its status and keep buyers informed."
    return None


assistant_service = AssistantService()
