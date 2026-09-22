"""SIH 2026 evaluation endpoints (/api/v1/sih/*, ADMIN + CLUSTER_MANAGER read).

Read-only surfaces are open to CLUSTER_MANAGER for transparency; writes are
ADMIN-only. Everything is evidence CRUD + real computation — no scoring magic.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import NotFoundError, ValidationFailedError
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
from app.schemas.sih import (
    ChecklistUpdateIn,
    CompetitorCellIn,
    FieldApprovalIn,
    ImpactMetricIn,
    JudgeAnswerIn,
    PriorArtIn,
    ProblemLinkIn,
    ReferenceIn,
    ResearchIn,
    RiskIn,
)
from app.security.dependencies import get_current_user, require_roles
from app.security.rate_limit import enforce
from app.services.sih_service import sih_service
from app.models.user import User

router = APIRouter(prefix="/sih", tags=["sih-evidence"])


@router.get("/readiness", summary="Five-criterion SIH readiness rollup",
            dependencies=[Depends(require_roles("ADMIN", "CLUSTER_MANAGER"))])
def readiness(db: Session = Depends(get_db)):
    return sih_service.readiness(db)


@router.patch("/checklist/{item_id}", summary="Update a checklist item (fill in real evidence)",
              dependencies=[Depends(require_roles("ADMIN"))])
def update_checklist(item_id: str, payload: ChecklistUpdateIn, db: Session = Depends(get_db)):
    item = db.get(SIHChecklistItem, item_id)
    if item is None:
        raise NotFoundError("Checklist item not found.")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    return sih_service._checklist_row(item)


@router.get("/research", summary="Research evidence records (interviews, surveys, market)",
            dependencies=[Depends(require_roles("ADMIN", "CLUSTER_MANAGER"))])
def list_research(research_type: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(ResearchRecord).order_by(ResearchRecord.created_at.desc())
    if research_type:
        q = q.filter(ResearchRecord.research_type == research_type)
    return [{
        "id": r.id, "research_type": r.research_type, "respondent_id": r.respondent_id,
        "respondent_type": r.respondent_type, "craft_category": r.craft_category,
        "location_district": r.location_district, "location_state": r.location_state,
        "interview_date": r.interview_date.isoformat() if r.interview_date else None,
        "language": r.language, "years_of_experience": r.years_of_experience,
        "pain_points": r.pain_points, "observations": r.observations, "quotes": r.quotes,
        "consent_status": r.consent_status, "key_finding": r.key_finding,
        "source_org": r.source_org, "source_url": r.source_url,
        "validation_status": r.validation_status, "notes": r.notes,
    } for r in q.all()]


@router.post("/research", summary="Record real research evidence (anonymized)",
             dependencies=[Depends(require_roles("ADMIN"))])
def add_research(payload: ResearchIn, user: User = Depends(require_roles("ADMIN")),
                 db: Session = Depends(get_db)):
    row = ResearchRecord(**payload.model_dump(), created_by=user.id,
                         validation_status="COMPLETE" if payload.consent_status in ("GRANTED", "ANONYMIZED") else "PENDING_VALIDATION")
    db.add(row)
    db.commit()
    return {"id": row.id, "status": row.validation_status}


@router.get("/problem-links", summary="Problem → Evidence → Feature → Metric matrix",
            dependencies=[Depends(require_roles("ADMIN", "CLUSTER_MANAGER"))])
def problem_links(db: Session = Depends(get_db)):
    return [{
        "id": r.id, "problem": r.problem, "evidence": r.evidence, "feature": r.feature,
        "expected_outcome": r.expected_outcome, "validation_metric": r.validation_metric,
        "baseline": r.baseline, "target": r.target, "observed": r.observed, "unit": r.unit,
        "sample_size": r.sample_size, "evidence_source": r.evidence_source,
        "validation_status": r.validation_status,
    } for r in db.query(ProblemEvidenceLink).order_by(ProblemEvidenceLink.sort_order).all()]


@router.post("/problem-links", summary="Add a problem→evidence mapping",
             dependencies=[Depends(require_roles("ADMIN"))])
def add_problem_link(payload: ProblemLinkIn, db: Session = Depends(get_db)):
    row = ProblemEvidenceLink(**payload.model_dump(),
                              validation_status="COMPLETE" if payload.observed is not None else "PENDING_VALIDATION")
    db.add(row)
    db.commit()
    return {"id": row.id}


@router.get("/impact/computed", summary="Impact metrics computed from real platform rows",
            dependencies=[Depends(require_roles("ADMIN", "CLUSTER_MANAGER"))])
def impact_computed(db: Session = Depends(get_db)):
    computed = sih_service.computed_impact(db)
    manual = db.query(ImpactMetric).order_by(ImpactMetric.sort_order).all()
    return {"computed": computed,
            "manual_definitions": [{
                "id": m.id, "category": m.category, "code": m.code, "name": m.name,
                "direction": m.direction, "unit": m.unit, "baseline": m.baseline,
                "target": m.target, "actual": m.actual, "provenance": m.actual_provenance,
                "computed_actual": m.computed_actual, "source": m.source,
                "sample_size": m.sample_size, "validation_status": m.validation_status,
            } for m in manual]}


@router.post("/impact/{metric_code}/observation", summary="Attach a real observation to a metric",
             dependencies=[Depends(require_roles("ADMIN"))])
def metric_observation(metric_code: str, payload: ImpactMetricIn, db: Session = Depends(get_db)):
    m = db.query(ImpactMetric).filter(ImpactMetric.code == metric_code).first()
    if m is None:
        raise NotFoundError(f"Metric '{metric_code}' not defined.")
    m.actual = payload.actual
    m.actual_provenance = payload.provenance
    m.validation_status = "COMPLETE" if payload.provenance == "REAL" else payload.provenance
    if payload.baseline is not None:
        m.baseline = payload.baseline
    if payload.target is not None:
        m.target = payload.target
    m.sample_size = payload.sample_size
    m.source = payload.source or m.source
    db.commit()
    return {"code": m.code, "actual": m.actual, "provenance": m.actual_provenance}


@router.get("/innovation", summary="Innovation docs (statement, differentiation, traceability)",
            dependencies=[Depends(require_roles("ADMIN", "CLUSTER_MANAGER"))])
def innovation(db: Session = Depends(get_db)):
    return [{"id": r.id, "section": r.section, "title": r.title, "body": r.body,
             "workflow": r.workflow, "validation_status": r.validation_status}
            for r in db.query(InnovationDoc).order_by(InnovationDoc.sort_order).all()]


@router.get("/competitors", summary="Competitor capability matrix (sourced cells only)",
            dependencies=[Depends(require_roles("ADMIN", "CLUSTER_MANAGER"))])
def competitors(db: Session = Depends(get_db)):
    return [{"id": r.id, "competitor": r.competitor, "capability": r.capability, "value": r.value,
             "is_karvantana": r.is_karvantana, "source": r.source,
             "source_date": r.source_date.isoformat() if r.source_date else None,
             "verification_status": r.verification_status, "notes": r.notes}
            for r in db.query(CompetitorMatrixEntry).order_by(CompetitorMatrixEntry.competitor, CompetitorMatrixEntry.capability).all()]


@router.post("/competitors", summary="Set a competitor cell WITH its source",
             dependencies=[Depends(require_roles("ADMIN"))])
def set_competitor_cell(payload: CompetitorCellIn, db: Session = Depends(get_db)):
    row = db.query(CompetitorMatrixEntry).filter(
        CompetitorMatrixEntry.competitor == payload.competitor,
        CompetitorMatrixEntry.capability == payload.capability).first()
    if row is None:
        raise NotFoundError("That competitor/capability cell is not in the matrix.")
    row.value = payload.value
    row.source = payload.source
    row.notes = payload.notes
    row.source_date = datetime.now(timezone.utc)
    row.verification_status = "COMPLETE" if payload.source else "PENDING_VALIDATION"
    db.commit()
    return {"competitor": row.competitor, "capability": row.capability,
            "value": row.value, "verification_status": row.verification_status}


@router.get("/prior-art", summary="Prior-art / patent search log",
            dependencies=[Depends(require_roles("ADMIN", "CLUSTER_MANAGER"))])
def prior_art(db: Session = Depends(get_db)):
    return [{"id": r.id, "title": r.title, "source": r.source, "url": r.url,
             "date_accessed": r.date_accessed.isoformat() if r.date_accessed else None,
             "technology": r.technology, "relevance": r.relevance, "similarity": r.similarity,
             "differentiation": r.differentiation, "notes": r.notes,
             "validation_status": r.validation_status}
            for r in db.query(PriorArtRecord).order_by(PriorArtRecord.date_accessed.desc()).all()]


@router.post("/prior-art", summary="Log a performed prior-art search result",
             dependencies=[Depends(require_roles("ADMIN"))])
def add_prior_art(payload: PriorArtIn, db: Session = Depends(get_db)):
    row = PriorArtRecord(**payload.model_dump(), date_accessed=datetime.now(timezone.utc),
                         validation_status="COMPLETE")
    db.add(row)
    db.commit()
    return {"id": row.id}


@router.get("/tech-scouting", summary="Technology choices + AI pipeline documentation",
            dependencies=[Depends(require_roles("ADMIN", "CLUSTER_MANAGER"))])
def tech_scouting(db: Session = Depends(get_db)):
    return [{"id": r.id, "technology": r.technology, "layer": r.layer, "why": r.why,
             "alternatives": r.alternatives, "ai_input": r.ai_input, "ai_processing": r.ai_processing,
             "ai_model": r.ai_model, "ai_output": r.ai_output, "ai_validation": r.ai_validation,
             "ai_human_override": r.ai_human_override, "in_current_build": r.in_current_build}
            for r in db.query(TechScoutingRecord).order_by(TechScoutingRecord.layer, TechScoutingRecord.sort_order).all()]


@router.get("/risks", summary="Risk register",
            dependencies=[Depends(require_roles("ADMIN", "CLUSTER_MANAGER"))])
def risks(db: Session = Depends(get_db)):
    return [{"id": r.id, "risk_id": r.risk_id, "category": r.category, "description": r.description,
             "probability": r.probability, "impact": r.impact, "severity": r.severity,
             "mitigation": r.mitigation, "fallback": r.fallback, "owner": r.owner,
             "status": r.status, "validation": r.validation}
            for r in db.query(RiskRegisterEntry).order_by(RiskRegisterEntry.risk_id).all()]


@router.post("/risks", summary="Add or update a risk",
             dependencies=[Depends(require_roles("ADMIN"))])
def upsert_risk(payload: RiskIn, db: Session = Depends(get_db)):
    count = db.query(RiskRegisterEntry).count()
    row = RiskRegisterEntry(**payload.model_dump(), risk_id=f"R-{count + 1:02d}")
    db.add(row)
    db.commit()
    return {"id": row.id, "risk_id": row.risk_id}


@router.get("/judge-questions", summary="Judge Q&A center",
            dependencies=[Depends(require_roles("ADMIN", "CLUSTER_MANAGER"))])
def judge_questions(section: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(JudgeQuestion).order_by(JudgeQuestion.section, JudgeQuestion.sort_order)
    if section:
        q = q.filter(JudgeQuestion.section == section)
    return [{"id": r.id, "section": r.section, "question": r.question, "answer": r.answer,
             "feature_link": r.feature_link, "validation_status": r.validation_status}
            for r in q.all()]


@router.patch("/judge-questions/{qid}", summary="Answer a judge question (cite implemented reality only)",
              dependencies=[Depends(require_roles("ADMIN"))])
def answer_question(qid: str, payload: JudgeAnswerIn, db: Session = Depends(get_db)):
    row = db.get(JudgeQuestion, qid)
    if row is None:
        raise NotFoundError("Question not found.")
    row.answer = payload.answer
    row.feature_link = payload.feature_link
    row.validation_status = payload.validation_status
    db.commit()
    return {"id": row.id, "validation_status": row.validation_status}


@router.get("/references", summary="Research reference manager",
            dependencies=[Depends(require_roles("ADMIN", "CLUSTER_MANAGER"))])
def references(category: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(ReferenceSource).order_by(ReferenceSource.title)
    if category:
        q = q.filter(ReferenceSource.category == category)
    return [{"id": r.id, "title": r.title, "organization": r.organization, "url": r.url,
             "publication_date": r.publication_date.isoformat() if r.publication_date else None,
             "accessed_date": r.accessed_date.isoformat() if r.accessed_date else None,
             "key_finding": r.key_finding, "relevance": r.relevance,
             "criterion_supported": r.criterion_supported, "category": r.category,
             "validation_status": r.validation_status}
            for r in q.all()]


@router.post("/references", summary="Add a real reference",
             dependencies=[Depends(require_roles("ADMIN"))])
def add_reference(payload: ReferenceIn, db: Session = Depends(get_db)):
    row = ReferenceSource(**payload.model_dump(), accessed_date=datetime.now(timezone.utc))
    db.add(row)
    db.commit()
    return {"id": row.id}


@router.get("/evidence-pack", summary="Judge evidence pack (JSON)",
            dependencies=[Depends(require_roles("ADMIN", "CLUSTER_MANAGER"))])
def evidence_pack(db: Session = Depends(get_db)):
    return sih_service.evidence_pack(db)


@router.get("/evidence-pack/export", summary="Evidence pack as Markdown download")
def evidence_pack_download(db: Session = Depends(get_db)):
    md = sih_service.pack_markdown(db)
    buf = io.BytesIO(md.encode("utf-8"))
    return StreamingResponse(buf, media_type="text/markdown", headers={
        "Content-Disposition": "attachment; filename=karvantana-sih-evidence-pack.md"})


@router.get("/tests", summary="Real test report from the last pytest JUnit artifact")
def tests_report():
    return sih_service.test_report()


@router.post("/approvals", summary="Record a human-in-the-loop AI field decision",
             dependencies=[Depends(require_roles("ARTISAN", "ADMIN"))])
def record_approval(payload: FieldApprovalIn, request: Request,
                    user: User = Depends(require_roles("ARTISAN", "ADMIN")),
                    db: Session = Depends(get_db)):
    enforce("ai", user.id)
    row = AIFieldApproval(
        product_id=payload.product_id, ai_generation_id=payload.ai_generation_id,
        field=payload.field, original_output=payload.original_output,
        final_output=payload.final_output, action=payload.action,
        decided_by=user.id, decided_at=datetime.now(timezone.utc),
        confidence=payload.confidence,
    )
    db.add(row)
    db.commit()
    return {"id": row.id}
