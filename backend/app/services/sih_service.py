"""SIH evidence service: readiness rollup, real computed metrics, test reports.

Principle: every number returned here is either computed from actual platform
rows, read from a real measurement artifact (pytest JUnit XML), or explicitly
PENDING_VALIDATION. Nothing is estimated.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ai import AIGeneration
from app.models.commerce import BulkRequest, CustomRequest, Order, OrderItem, OrderStatus
from app.models.engagement import Follow, Review
from app.models.product import Product
from app.models.profile import ArtisanProfile
from app.models.user import User
from app.models.sih import (
    AIFieldApproval,
    CompetitorMatrixEntry,
    EvidencePackSection,
    ImpactMetric,
    InnovationDoc,
    JudgeQuestion,
    PriorArtRecord,
    ProblemEvidenceLink,
    ReferenceSource,
    ResearchRecord,
    RiskRegisterEntry,
    SIHChecklistItem,
    TechScoutingRecord,
)

CRITERIA = ("PROBLEM_FIT", "INNOVATION", "FEASIBILITY", "TECH_DEPTH", "PRESENTATION")

STATUS_WEIGHTS = {
    "COMPLETE": 1.0,
    "DEMO_READY": 1.0,
    "PARTIALLY_COMPLETE": 0.5,
    "PENDING_VALIDATION": 0.25,
    "MISSING": 0.0,
}


def _pct(n: float, d: float) -> Optional[float]:
    return round(100.0 * n / d, 1) if d else None


class SIHService:
    # ------------------------------------------------------------- readiness
    def readiness(self, db: Session) -> dict:
        items = db.query(SIHChecklistItem).order_by(SIHChecklistItem.sort_order).all()
        by_criterion: dict[str, list] = {}
        for it in items:
            by_criterion.setdefault(it.criterion, []).append(it)
        criteria = []
        for c in CRITERIA:
            rows = by_criterion.get(c, [])
            total_w = sum(r.weight for r in rows) or 1.0
            earned = sum(STATUS_WEIGHTS.get(r.status, 0.0) * r.weight for r in rows)
            criteria.append({
                "criterion": c,
                "weight_pct": 20,
                "completion_pct": _pct(earned, total_w),
                "total": len(rows),
                "complete": sum(1 for r in rows if r.status in ("COMPLETE", "DEMO_READY")),
                "partial": sum(1 for r in rows if r.status == "PARTIALLY_COMPLETE"),
                "pending": sum(1 for r in rows if r.status == "PENDING_VALIDATION"),
                "missing": sum(1 for r in rows if r.status == "MISSING"),
                "demo_ready": all(r.demo_ready for r in rows) if rows else False,
                "items": [self._checklist_row(r) for r in rows],
            })
        # criteria percentages are already 0-100; the overall is their plain average
        overall = round(sum((c["completion_pct"] or 0) for c in criteria) / len(criteria), 1) if criteria else 0.0
        return {"criteria": criteria, "overall_pct": overall,
                "generated_at": datetime.now(timezone.utc).isoformat()}

    def _checklist_row(self, it: SIHChecklistItem) -> dict:
        return {
            "id": it.id, "code": it.code, "requirement": it.requirement,
            "evidence": it.evidence, "missing": it.missing, "status": it.status,
            "feature_link": it.feature_link, "doc_link": it.doc_link,
            "demo_ready": it.demo_ready, "weight": it.weight,
        }

    # ------------------------------------------------- real computed metrics
    def computed_impact(self, db: Session) -> dict:
        """Impact metrics computed from actual platform rows, with real sample
        sizes. Everything here is REAL — the demo DB is real (demo-labeled)
        data, which we disclose via `dataset`."""
        PAID = (OrderStatus.CONFIRMED, OrderStatus.PROCESSING, OrderStatus.IN_PRODUCTION,
                OrderStatus.READY_TO_SHIP, OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.COMPLETED)

        artisan_count = int(db.query(func.count(ArtisanProfile.id)).scalar() or 0)
        product_count = int(db.query(func.count(Product.id)).filter(Product.deleted_at.is_(None)).scalar() or 0)
        published = int(db.query(func.count(Product.id)).filter(
            Product.deleted_at.is_(None), Product.lifecycle == "PUBLISHED").scalar() or 0)
        order_count = int(db.query(func.count(Order.id)).scalar() or 0)
        bulk_count = int(db.query(func.count(BulkRequest.id)).scalar() or 0)
        custom_count = int(db.query(func.count(CustomRequest.id)).scalar() or 0)
        review_count = int(db.query(func.count(Review.id)).scalar() or 0)
        follow_count = int(db.query(func.count(Follow.id)).scalar() or 0)

        aov_row = db.query(func.avg(Order.total)).filter(Order.status.in_(PAID)).scalar()
        aov = round(float(aov_row), 2) if aov_row else None

        paid_orders = db.query(Order.id, Order.buyer_id).filter(Order.status.in_(PAID)).all()
        buyer_orders: dict[str, set[str]] = {}
        for oid, bid in paid_orders:
            buyer_orders.setdefault(bid, set()).add(oid)
        repeat_buyers = sum(1 for o in buyer_orders.values() if len(o) > 1)

        # repeat-order rate per buyer-artisan pair (orders beyond the first pair)
        pairs = (
            db.query(OrderItem.artisan_id, Order.buyer_id, func.count(func.distinct(OrderItem.order_id)))
            .join(Order, OrderItem.order_id == Order.id)
            .filter(Order.status.in_(PAID))
            .group_by(OrderItem.artisan_id, Order.buyer_id)
            .all()
        )
        multi = sum(1 for _, _, n in pairs if n > 1)
        repeat_rate = _pct(multi, len(pairs))

        # AI performance from real generation + approval records
        gens = int(db.query(func.count(AIGeneration.id)).filter(AIGeneration.task == "catalogue").scalar() or 0)
        approved = db.query(AIFieldApproval.action, func.count(AIFieldApproval.id)).group_by(AIFieldApproval.action).all()
        approval_counts = {a: int(n) for a, n in approved}
        corrected = int(db.query(func.count(AIGeneration.id)).filter(AIGeneration.corrected.isnot(None)).scalar() or 0)
        low_conf = int(db.query(func.count(AIGeneration.id)).filter(
            AIGeneration.confidence.isnot(None), AIGeneration.confidence < 0.75).scalar() or 0)
        avg_conf_row = db.query(func.avg(AIGeneration.confidence)).filter(
            AIGeneration.task == "catalogue", AIGeneration.confidence.isnot(None)).scalar()
        avg_conf = round(float(avg_conf_row), 3) if avg_conf_row else None

        latency_row = db.query(func.avg(AIGeneration.latency_ms)).filter(
            AIGeneration.task == "catalogue", AIGeneration.latency_ms.isnot(None)).scalar()
        avg_latency = round(float(latency_row), 1) if latency_row else None

        return {
            "dataset": "Demo seed dataset (clearly labeled demo users/products/orders) — real database rows, not fabricated numbers",
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "digital_enablement": {
                "artisans_onboarded": {"value": artisan_count, "sample": artisan_count},
                "products_digitized": {"value": product_count, "sample": product_count},
                "products_published": {"value": published, "sample": product_count,
                                       "pct": _pct(published, product_count)},
                "ai_assisted_listings": {"value": gens, "sample": product_count},
            },
            "market_access": {
                "b2b_bulk_requests": {"value": bulk_count},
                "custom_requests": {"value": custom_count},
                "follows": {"value": follow_count},
                "reviews": {"value": review_count},
            },
            "commerce": {
                "orders_total": {"value": order_count},
                "orders_paid_statuses": {"value": len(paid_orders)},
                "average_order_value_inr": {"value": aov, "sample": len(paid_orders)},
                "repeat_buyers": {"value": repeat_buyers, "sample": len(buyer_orders)},
                "repeat_buyer_pct": {"value": _pct(repeat_buyers, len(buyer_orders)), "sample": len(buyer_orders)},
                "artisan_buyer_repeat_order_pct": {"value": repeat_rate, "sample": len(pairs)},
            },
            "artisan_business": {
                "artisans_with_orders": {
                    "value": int(db.query(func.count(func.distinct(OrderItem.artisan_id))).scalar() or 0),
                    "sample": artisan_count},
            },
            "ai_performance": {
                "catalogue_generations": {"value": gens},
                "ai_acceptance": {"value": approval_counts.get("APPROVE", 0), "sample": sum(approval_counts.values())},
                "ai_edits": {"value": approval_counts.get("EDIT", 0)},
                "ai_rejections": {"value": approval_counts.get("REJECT", 0)},
                "ai_regenerations": {"value": approval_counts.get("REGENERATE", 0)},
                "generations_with_artisan_edits": {"value": corrected, "sample": gens},
                "low_confidence_generations_lt_0_75": {"value": low_conf, "sample": gens},
                "avg_catalogue_confidence": {"value": avg_conf, "sample": gens},
                "avg_catalogue_latency_ms": {"value": avg_latency, "sample": gens},
            },
        }

    # ------------------------------------------------------------ test report
    def test_report(self) -> dict:
        """Read the last pytest JUnit XML artifact if present. Never invented."""
        path = os.environ.get("KARVANTANA_TEST_REPORT", "test-results.xml")
        if not os.path.exists(path):
            return {"available": False,
                    "note": "No test report artifact yet. Run: python3 -m pytest tests/ --junitxml=test-results.xml"}
        try:
            import xml.etree.ElementTree as ET
            root = ET.parse(path).getroot()
            suite = root.find("testsuite") if root.tag == "testsuites" else root
            assert suite is not None
            total = int(suite.get("tests", 0))
            fails = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
            skipped = int(suite.get("skipped", 0))
            t = float(suite.get("time", 0))
            return {"available": True, "total": total, "passed": total - fails - skipped,
                    "failed": fails, "skipped": skipped, "duration_s": round(t, 2),
                    "source": os.path.abspath(path),
                    "generated_at": datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc).isoformat()}
        except Exception as e:  # malformed artifact — say so, don't guess
            return {"available": False, "error": f"Test report unreadable: {e}"}

    # ---------------------------------------------------------- pack assembly
    def evidence_pack(self, db: Session) -> dict:
        sections: dict[str, list] = {}
        for row in db.query(EvidencePackSection).order_by(EvidencePackSection.section, EvidencePackSection.sort_order).all():
            sections.setdefault(row.section, []).append({
                "claim": row.claim, "evidence": row.evidence, "source": row.source,
                "feature": row.feature, "metric": row.metric, "demo_proof": row.demo_proof,
                "status": row.status,
            })
        return {"sections": sections, "generated_at": datetime.now(timezone.utc).isoformat()}

    def pack_markdown(self, db: Session) -> str:
        pack = self.evidence_pack(db)
        risks = db.query(RiskRegisterEntry).order_by(RiskRegisterEntry.risk_id).all()
        lines = ["# KARVANTANA — SIH Evidence Pack", "",
                 "> Generated from the live platform evidence database. Rows marked",
                 "> PENDING VALIDATION are real gaps, not hidden failures.", "",
                 f"_Generated: {pack['generated_at']}_", ""]
        for sec, rows in pack["sections"].items():
            lines += [f"## {sec.replace('_', ' ').title()}", ""]
            for r in rows:
                lines.append(f"- **Claim:** {r['claim']}")
                lines.append(f"  - Evidence: {r['evidence'] or '—'}")
                lines.append(f"  - Source: {r['source'] or '—'} · Feature: {r['feature'] or '—'}")
                lines.append(f"  - Metric: {r['metric'] or '—'} · Demo proof: {r['demo_proof'] or '—'}")
                lines.append(f"  - Status: **{r['status']}**")
            lines.append("")
        lines += ["## Risk Register", "", "| ID | Risk | Severity | Mitigation status |", "|---|---|---|---|"]
        for rk in risks:
            lines.append(f"| {rk.risk_id} | {rk.description[:90]} | {rk.severity} | {rk.status} |")
        lines.append("")
        return "\n".join(lines)


sih_service = SIHService()
