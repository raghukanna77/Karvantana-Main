"""SIH evidence schemas. Privacy by design: research records accept anonymized
respondent codes and district/state only — no names, phones or emails."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ChecklistUpdateIn(BaseModel):
    evidence: Optional[str] = None
    missing: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(COMPLETE|PARTIALLY_COMPLETE|PENDING_VALIDATION|MISSING|DEMO_READY)$")
    feature_link: Optional[str] = None
    doc_link: Optional[str] = None
    demo_ready: Optional[bool] = None


class ResearchIn(BaseModel):
    research_type: str = Field(pattern="^(INTERVIEW|SURVEY|MARKET|GOVERNMENT|COMPETITOR|PROBLEM_VALIDATION|IMPACT)$")
    respondent_id: Optional[str] = Field(None, max_length=60)
    respondent_type: Optional[str] = Field(None, max_length=40)
    craft_category: Optional[str] = Field(None, max_length=80)
    location_district: Optional[str] = Field(None, max_length=80)
    location_state: Optional[str] = Field(None, max_length=80)
    interview_date: Optional[str] = None
    language: Optional[str] = Field(None, max_length=10)
    years_of_experience: Optional[int] = Field(None, ge=0, le=100)
    pain_points: Optional[dict] = None
    observations: Optional[dict] = None
    quotes: Optional[dict] = None
    consent_status: str = Field("PENDING", pattern="^(GRANTED|PENDING|DECLINED|ANONYMIZED)$")
    evidence_url: Optional[str] = Field(None, max_length=400)
    key_finding: Optional[str] = None
    source_org: Optional[str] = Field(None, max_length=160)
    source_url: Optional[str] = Field(None, max_length=400)
    notes: Optional[str] = None


class ProblemLinkIn(BaseModel):
    problem: str
    evidence: Optional[str] = None
    feature: str
    expected_outcome: Optional[str] = None
    validation_metric: Optional[str] = None
    baseline: Optional[float] = None
    target: Optional[float] = None
    observed: Optional[float] = None
    unit: Optional[str] = Field(None, max_length=30)
    sample_size: Optional[int] = Field(None, ge=0)
    evidence_source: Optional[str] = None


class ImpactMetricIn(BaseModel):
    actual: float
    provenance: str = Field("REAL", pattern="^(REAL|SIMULATED|DEMO|TARGET|PENDING_VALIDATION)$")
    baseline: Optional[float] = None
    target: Optional[float] = None
    sample_size: Optional[int] = Field(None, ge=0)
    source: Optional[str] = None


class CompetitorCellIn(BaseModel):
    competitor: str = Field(max_length=80)
    capability: str = Field(max_length=80)
    value: str = Field(pattern="^(YES|NO|PARTIAL|NETWORK_DEPENDENT|NOT_IDENTIFIED|NOT_EVALUATED)$")
    source: Optional[str] = None
    notes: Optional[str] = None


class PriorArtIn(BaseModel):
    title: str = Field(max_length=300)
    source: str = Field(max_length=200)
    url: Optional[str] = Field(None, max_length=400)
    technology: Optional[str] = Field(None, max_length=160)
    relevance: Optional[str] = None
    similarity: Optional[str] = None
    differentiation: Optional[str] = None
    notes: Optional[str] = None


class RiskIn(BaseModel):
    category: str = Field(max_length=40)
    description: str
    probability: str = Field("MEDIUM", pattern="^(LOW|MEDIUM|HIGH)$")
    impact: str = Field("HIGH", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    mitigation: str
    fallback: Optional[str] = None
    owner: Optional[str] = Field(None, max_length=80)
    status: str = Field("MITIGATION_PLANNED", pattern="^(MITIGATED_IN_BUILD|MITIGATION_PLANNED|OPEN)$")
    validation: Optional[str] = None


class ReferenceIn(BaseModel):
    title: str = Field(max_length=300)
    organization: Optional[str] = Field(None, max_length=160)
    url: Optional[str] = Field(None, max_length=400)
    key_finding: Optional[str] = None
    relevance: Optional[str] = None
    criterion_supported: Optional[str] = Field(None, max_length=40)
    category: Optional[str] = Field(None, max_length=40)


class JudgeAnswerIn(BaseModel):
    answer: str
    feature_link: Optional[str] = None
    validation_status: str = Field("COMPLETE", pattern="^(COMPLETE|PENDING_VALIDATION)$")


class FieldApprovalIn(BaseModel):
    product_id: str = Field(max_length=36)
    ai_generation_id: Optional[str] = Field(None, max_length=36)
    field: str = Field(max_length=60)
    original_output: Optional[dict] = None
    final_output: Optional[dict] = None
    action: str = Field(pattern="^(APPROVE|EDIT|REJECT|REGENERATE)$")
    confidence: Optional[float] = Field(None, ge=0, le=1)
