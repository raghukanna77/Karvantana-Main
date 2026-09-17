"""Analytics, admin, clusters, client events, catalogue export (/api/v1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.ai import AIGeneration, AIUsage
from app.models.analytics import AuditLog
from app.models.commerce import Order, OrderItem, OrderStatus
from app.models.engagement import Dispute
from app.models.product import Product
from app.models.profile import ArtisanProfile, Cluster, ClusterMember
from app.models.user import User
from app.security.dependencies import get_current_user, require_roles
from app.services.analytics_service import analytics_service

router = APIRouter(tags=["analytics"])


@router.get("/analytics/artisan/dashboard", summary="Artisan business dashboard",
            dependencies=[Depends(require_roles("ARTISAN", "ADMIN"))])
def artisan_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
    if profile is None:
        raise NotFoundError("Complete artisan onboarding first.")
    return analytics_service.artisan_dashboard(db, artisan_id=profile.id)


@router.get("/analytics/admin/overview", summary="Admin platform overview",
            dependencies=[Depends(require_roles("ADMIN"))])
def admin_overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analytics_service.admin_overview(db)


@router.get("/analytics/impact", summary="Impact metrics (computed from real records)")
def impact(db: Session = Depends(get_db)):
    return analytics_service.impact(db)


@router.get("/admin/ai/monitoring", summary="AI governance dashboard", dependencies=[Depends(require_roles("ADMIN"))])
def ai_monitoring(db: Session = Depends(get_db)):
    total = int(db.query(func.count(AIUsage.id)).scalar() or 0)
    failed = int(db.query(func.count(AIUsage.id)).filter(AIUsage.success.is_(False)).scalar() or 0)
    avg_latency = db.query(func.avg(AIUsage.latency_ms)).scalar() or 0
    low_conf = int(
        db.query(func.count(AIGeneration.id)).filter(AIGeneration.confidence.isnot(None), AIGeneration.confidence < 0.75).scalar() or 0
    )
    corrections = int(db.query(func.count(AIGeneration.id)).filter(AIGeneration.corrected.isnot(None)).scalar() or 0)
    by_task = (
        db.query(AIUsage.task, func.count(AIUsage.id), func.avg(AIUsage.latency_ms))
        .group_by(AIUsage.task)
        .all()
    )
    return {
        "requests": total,
        "failed": failed,
        "success_rate": round((total - failed) / total * 100, 1) if total else None,
        "avg_latency_ms": int(avg_latency),
        "low_confidence_outputs": low_conf,
        "human_corrections": corrections,
        "estimated_cost_usd": float(db.query(func.coalesce(func.sum(AIUsage.estimated_cost_usd), 0.0)).scalar() or 0.0),
        "by_task": [{"task": t, "requests": int(c), "avg_latency_ms": int(l or 0)} for t, c, l in by_task],
    }


@router.get("/admin/audit-logs", summary="Audit trail", dependencies=[Depends(require_roles("ADMIN"))])
def audit_logs(db: Session = Depends(get_db)):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    return {"items": [
        {"id": a.id, "action": a.action, "actor_id": a.actor_id, "detail": a.detail,
         "created_at": a.created_at.isoformat()} for a in rows
    ]}


@router.get("/admin/moderation/products", summary="Product moderation queue", dependencies=[Depends(require_roles("ADMIN"))])
def moderation_queue(db: Session = Depends(get_db)):
    rows = (
        db.query(Product, ArtisanProfile.display_name)
        .join(ArtisanProfile, Product.artisan_id == ArtisanProfile.id)
        .filter(Product.lifecycle.in_(["REVIEW_REQUIRED", "PUBLISHED"]))
        .order_by(Product.updated_at.desc())
        .limit(50)
        .all()
    )
    return {"items": [
        {"id": p.id, "title": p.title or "(untitled)", "artisan": name, "lifecycle": p.lifecycle,
         "price": float(p.price or 0), "updated_at": p.updated_at.isoformat()} for p, name in rows
    ]}


@router.get("/admin/disputes", summary="Dispute list", dependencies=[Depends(require_roles("ADMIN"))])
def disputes(db: Session = Depends(get_db)):
    rows = db.query(Dispute).order_by(Dispute.created_at.desc()).limit(50).all()
    return {"items": [
        {"id": d.id, "order_id": d.order_id, "reason": d.reason, "status": d.status,
         "created_at": d.created_at.isoformat()} for d in rows
    ]}


# ------------------------------------------------------------------ clusters

@router.get("/clusters/me", summary="My cluster (cluster manager)", dependencies=[Depends(require_roles("CLUSTER_MANAGER", "ADMIN"))])
def my_cluster(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cluster = db.query(Cluster).filter(Cluster.manager_id == user.id).first()
    if cluster is None:
        raise NotFoundError("No cluster assigned. Ask an admin to create one.")
    return cluster_payload(db, cluster)


def cluster_payload(db: Session, cluster: Cluster) -> dict:
    members = (
        db.query(ClusterMember, ArtisanProfile)
        .join(ArtisanProfile, ClusterMember.artisan_id == ArtisanProfile.id)
        .filter(ClusterMember.cluster_id == cluster.id)
        .all()
    )
    analytics = analytics_service.cluster_analytics(db, cluster_id=cluster.id)
    return {
        "id": cluster.id, "name": cluster.name, "region": cluster.region,
        "analytics": analytics,
        "artisans": [
            {"id": p.id, "display_name": p.display_name, "craft": p.craft_specialization,
             "state": p.state, "onboarding_complete": p.onboarding_complete}
            for _, p in members
        ],
    }


@router.post("/clusters/{cluster_id}/artisans", summary="Onboard an artisan into my cluster",
             dependencies=[Depends(require_roles("CLUSTER_MANAGER", "ADMIN"))])
def add_artisan(cluster_id: str, payload: dict, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if cluster is None:
        raise NotFoundError("Cluster not found.")
    if user.role != "ADMIN" and cluster.manager_id != user.id:
        raise PermissionDeniedError("You manage a different cluster.")
    artisan_user_id = str(payload.get("artisan_user_id", ""))
    artisan_user = db.query(User).filter(User.id == artisan_user_id, User.role == "ARTISAN").first()
    if artisan_user is None:
        raise NotFoundError("Artisan account not found.")
    profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == artisan_user.id).first()
    if profile is None:
        raise NotFoundError("That artisan hasn't completed onboarding.")
    if not db.query(ClusterMember).filter(ClusterMember.cluster_id == cluster.id,
                                          ClusterMember.artisan_id == profile.id).first():
        db.add(ClusterMember(cluster_id=cluster.id, artisan_id=profile.id))
        db.flush()
    return cluster_payload(db, cluster)


# -------------------------------------------------------------- client events

EVENT_ALLOWLIST = {
    "PRODUCT_VIEWED", "SEARCH_PERFORMED", "BUYER_ENQUIRY_CREATED", "ARTISAN_FOLLOWED",
    "SAVED_PRODUCT", "REORDER_CREATED", "PRODUCT_SHARED",
}


@router.post("/events", summary="Client analytics ingestion (rate-limited, allow-listed)")
async def ingest_event(request: Request, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    from app.security.rate_limit import enforce

    enforce("search", user.id)
    body = await request.json()
    event_type = str(body.get("event_type", ""))
    if event_type not in EVENT_ALLOWLIST:
        from app.core.errors import ValidationFailedError

        raise ValidationFailedError("Unknown event type.")
    analytics_service.track(db, event_type=event_type, actor=user,
                            entity_type=body.get("entity_type"),
                            entity_id=body.get("entity_id"),
                            payload=body.get("payload"))
    return {"tracked": True}


# ------------------------------------------------------- catalogue export

@router.get("/export/catalogue", summary="Canonical catalogue export (JSON) for commerce networks",
            dependencies=[Depends(require_roles("ARTISAN", "ADMIN"))])
def export_catalogue(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Standardized representation ready for ONDC/IndiaHandmade-shaped adapters
    (blueprint §59, §61). Demo adapter — clearly labeled, no live network claims."""
    from app.core.feature_flags import is_enabled

    profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
    if profile is None:
        raise NotFoundError("Complete artisan onboarding first.")
    products = (
        db.query(Product)
        .filter(Product.artisan_id == profile.id, Product.lifecycle == "PUBLISHED", Product.deleted_at.is_(None))
        .all()
    )

    def canonical(p: Product) -> dict:
        return {
            "product_id": p.id,
            "title": p.title,
            "description": {"short": p.short_description, "full": p.description},
            "category": p.category_id,
            "materials": [p.material] if p.material else [],
            "craft": {"technique": p.technique, "origin": p.origin},
            "dimensions": p.dimensions,
            "pricing": {"unit": float(p.price or 0), "currency": p.currency,
                        "bulk": {"moq": p.bulk_moq, "price": float(p.bulk_price) if p.bulk_price else None}},
            "inventory": {"mode": p.inventory_mode, "stock": p.stock_quantity,
                          "production_days": p.production_days},
            "artisan": {"id": profile.id, "name": profile.display_name, "state": profile.state},
            "media": [i.original_url for i in p.images],
            "customization": p.customization_available,
            "keywords": (p.keywords or "").split(", ") if p.keywords else [],
        }

    return {
        "format": "karvantana.catalogue.v1",
        "adapter_note": "Canonical export for commerce-network adapters (DEMO — no live network connection).",
        "artisan": {"id": profile.id, "name": profile.display_name, "state": profile.state},
        "products": [canonical(p) for p in products],
    }
