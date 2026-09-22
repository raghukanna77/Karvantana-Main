"""SIH 2026 evaluation evidence models.

Everything here is EVIDENCE INFRASTRUCTURE: records that a team fills in with
real data over time. The system never fabricates values — every metric, claim
and research record carries an explicit validation status and provenance, and
seeded content is marked DEMO where it is illustrative.

Core principle (brief §27): distinguish IMPLEMENTED / PARTIAL / PLANNED /
SIMULATED / DEMO / VALIDATED / PENDING VALIDATION. Never blur them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin, UUIDPkMixin, utcnow

# Shared vocabularies (validated against nothing — these are just enums)
EVIDENCE_STATUSES = ("COMPLETE", "PARTIALLY_COMPLETE", "PENDING_VALIDATION", "MISSING", "DEMO_READY")
DATA_PROVENANCES = ("REAL", "SIMULATED", "DEMO", "TARGET", "PENDING_VALIDATION")
SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


class SIHChecklistItem(UUIDPkMixin, TimestampMixin, Base):
    """One line of the five-criterion SIH rubric with its real evidence links."""

    __tablename__ = "sih_checklist_items"
    __table_args__ = (UniqueConstraint("criterion", "code", name="uq_sih_checklist_code"),)

    criterion: Mapped[str] = mapped_column(String(40), index=True)  # PROBLEM_FIT|INNOVATION|FEASIBILITY|TECH_DEPTH|PRESENTATION
    code: Mapped[str] = mapped_column(String(80))                   # stable slug, e.g. "pf-user-research"
    requirement: Mapped[str] = mapped_column(Text)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)      # what actually exists
    missing: Mapped[Optional[str]] = mapped_column(Text, nullable=True)       # what is still absent
    status: Mapped[str] = mapped_column(String(30), default="MISSING")        # EVIDENCE_STATUSES
    feature_link: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # in-app route or module path
    doc_link: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)      # docs/… path
    demo_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)        # relative weight inside its criterion
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ResearchRecord(UUIDPkMixin, TimestampMixin, Base):
    """User interviews / surveys / market research. Privacy by default:
    store respondent IDs + district/state only — never names or phone numbers."""

    __tablename__ = "sih_research_records"
    __table_args__ = (Index("ix_sih_research_type_date", "research_type", "interview_date"),)

    research_type: Mapped[str] = mapped_column(String(40), index=True)  # INTERVIEW|SURVEY|MARKET|GOVERNMENT|COMPETITOR|PROBLEM_VALIDATION|IMPACT
    respondent_id: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)  # anonymized code
    respondent_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)  # ARTISAN|WEAVER|MICRO_ENTREPRENEUR|BUYER|NGO|FACILITATOR
    craft_category: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    location_district: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    location_state: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    interview_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    years_of_experience: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pain_points: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {pricing: bool, photography: bool, ...}
    observations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) # digital literacy, channels, difficulties
    quotes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)       # {lang: text} direct quotes with consent
    consent_status: Mapped[str] = mapped_column(String(20), default="PENDING")  # GRANTED|PENDING|DECLINED|ANONYMIZED
    evidence_url: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)  # attachment link
    key_finding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_org: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)  # for market/gov research
    source_url: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    source_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # publication date
    accessed_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="PENDING_VALIDATION")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class ProblemEvidenceLink(UUIDPkMixin, TimestampMixin, Base):
    """Problem → Evidence → Feature → Expected outcome → Validation metric."""

    __tablename__ = "sih_problem_links"

    problem: Mapped[str] = mapped_column(Text)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # reference to research record / source
    feature: Mapped[str] = mapped_column(String(200))                      # KARVANTANA feature + where it lives
    expected_outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validation_metric: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    baseline: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    observed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # minutes|count|percent|…
    sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    evidence_source: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="PENDING_VALIDATION")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ImpactMetric(UUIDPkMixin, TimestampMixin, Base):
    """Impact metric definition + observations. `actual` may be filled by the
    platform computation endpoint; manual entries must declare provenance."""

    __tablename__ = "sih_impact_metrics"
    __table_args__ = (UniqueConstraint("category", "code", name="uq_sih_impact_code"),)

    category: Mapped[str] = mapped_column(String(40), index=True)  # DIGITAL_ENABLEMENT|MARKET_ACCESS|COMMERCE|ARTISAN_BUSINESS|AI_PERFORMANCE
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(160))
    direction: Mapped[str] = mapped_column(String(10), default="UP")  # UP|DOWN — which way is good
    unit: Mapped[str] = mapped_column(String(30), default="count")
    baseline: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual: Mapped[Optional[float]] = mapped_column(Float, nullable=True)      # manual entry
    actual_provenance: Mapped[str] = mapped_column(String(30), default="PENDING_VALIDATION")  # DATA_PROVENANCES
    computed_actual: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # filled by /sih/impact/computed from real DB rows
    source: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="PENDING_VALIDATION")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class InnovationDoc(UUIDPkMixin, TimestampMixin, Base):
    """Innovation statement, differentiation, workflow, traceability (text blocks)."""

    __tablename__ = "sih_innovation_docs"

    section: Mapped[str] = mapped_column(String(60), index=True)  # STATEMENT|COMPETITIVE|TECH_SCOUTING|PRIOR_ART|DIFFERENTIATION|TRACEABILITY
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    workflow: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # ordered stages for visual flows
    validation_status: Mapped[str] = mapped_column(String(30), default="PENDING_VALIDATION")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class CompetitorMatrixEntry(UUIDPkMixin, TimestampMixin, Base):
    """One competitor × capability cell. Never claim a gap without a source."""

    __tablename__ = "sih_competitor_matrix"
    __table_args__ = (UniqueConstraint("competitor", "capability", name="uq_sih_comp_cell"),)

    competitor: Mapped[str] = mapped_column(String(80), index=True)
    capability: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(String(30), default="NOT_EVALUATED")  # YES|NO|PARTIAL|NETWORK_DEPENDENT|NOT_IDENTIFIED|NOT_EVALUATED
    is_karvantana: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    source_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="PENDING_VALIDATION")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PriorArtRecord(UUIDPkMixin, TimestampMixin, Base):
    """Patent / prior-art / academic search log. Records *performed searches*,
    never the claim that nothing exists."""

    __tablename__ = "sih_prior_art"

    title: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(200))                 # Google Patents|arXiv|product page…
    url: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    date_accessed: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    technology: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    relevance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # HIGH|MEDIUM|LOW + why
    similarity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    differentiation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="PENDING_VALIDATION")


class TechScoutingRecord(UUIDPkMixin, TimestampMixin, Base):
    """Why each technology is used + AI/ML input→output documentation."""

    __tablename__ = "sih_tech_scouting"

    technology: Mapped[str] = mapped_column(String(120))
    layer: Mapped[str] = mapped_column(String(40), index=True)  # FRONTEND|BACKEND|DATA|AI|INFRA|OFFLINE
    why: Mapped[str] = mapped_column(Text)
    alternatives: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # AI/ML pipeline documentation (null for non-AI rows):
    ai_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_processing: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_validation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_human_override: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    in_current_build: Mapped[bool] = mapped_column(Boolean, default=True)  # False = future/planned
    validation_status: Mapped[str] = mapped_column(String(30), default="COMPLETE")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class RiskRegisterEntry(UUIDPkMixin, TimestampMixin, Base):
    """Feasibility risk register with real mitigation status."""

    __tablename__ = "sih_risks"

    risk_id: Mapped[str] = mapped_column(String(20), unique=True)   # R-01…
    category: Mapped[str] = mapped_column(String(40), index=True)   # USER|TECH|AI|MARKET|OPERATIONS|SECURITY|PRIVACY|FINANCIAL
    description: Mapped[str] = mapped_column(Text)
    probability: Mapped[str] = mapped_column(String(10), default="MEDIUM")  # LOW|MEDIUM|HIGH
    impact: Mapped[str] = mapped_column(String(10), default="HIGH")
    severity: Mapped[str] = mapped_column(String(10), default="HIGH")
    mitigation: Mapped[str] = mapped_column(Text)
    fallback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="MITIGATION_PLANNED")  # MITIGATED_IN_BUILD|MITIGATION_PLANNED|OPEN
    validation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # where the mitigation can be seen
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class JudgeQuestion(UUIDPkMixin, TimestampMixin, Base):
    """Judge Q&A center. `answer` must only cite implemented reality."""

    __tablename__ = "sih_judge_questions"

    section: Mapped[str] = mapped_column(String(30), index=True)  # PROBLEM|INNOVATION|TECHNICAL|FEASIBILITY|BUSINESS|IMPACT
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feature_link: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="PENDING_VALIDATION")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ReferenceSource(UUIDPkMixin, TimestampMixin, Base):
    """Research/reference manager — real citations only."""

    __tablename__ = "sih_references"

    title: Mapped[str] = mapped_column(String(300))
    organization: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    publication_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    accessed_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    key_finding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relevance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    criterion_supported: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)  # PROBLEM_FIT|…
    category: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="PENDING_VALIDATION")


class EvidencePackSection(UUIDPkMixin, TimestampMixin, Base):
    """SIH Evidence Pack rows: CLAIM → EVIDENCE → SOURCE → FEATURE → METRIC → DEMO PROOF → STATUS."""

    __tablename__ = "sih_evidence_pack"

    section: Mapped[str] = mapped_column(String(60), index=True)  # PROBLEM_FIT|USER_RESEARCH|…|REFERENCES
    claim: Mapped[str] = mapped_column(Text)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    feature: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    metric: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    demo_proof: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING_VALIDATION")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class AIFieldApproval(UUIDPkMixin, TimestampMixin, Base):
    """Human-in-the-loop decision record for one AI-generated catalogue field.

    Rows are written when an artisan approves/edits/rejects/regenerates a field
    in the product wizard; `ai_generation_id` ties back to the auditable
    AIGeneration row so original AI output and human outcome stay linked.
    """

    __tablename__ = "ai_field_approvals"
    __table_args__ = (Index("ix_ai_approval_product", "product_id", "created_at"),)

    product_id: Mapped[str] = mapped_column(String(36), index=True)
    ai_generation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    field: Mapped[str] = mapped_column(String(60))                  # title|short_description|full_description|price|…
    original_output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # AI output verbatim
    final_output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)     # after human edit
    action: Mapped[str] = mapped_column(String(20))                 # APPROVE|EDIT|REJECT|REGENERATE
    decided_by: Mapped[str] = mapped_column(String(36), index=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
