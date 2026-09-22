# KARVANTANA — SIH 2026 Readiness & Evidence Guide

> This document explains the **evidence system** and where every rubric claim
> lives. It contains **no invented numbers**: anything not yet measured is
> marked PENDING VALIDATION, and the platform enforces that discipline in code.

## The evidence system in one paragraph

KARVANTANA separates **what is built** from **what is proven**. The backend
exposes an evidence API (`/api/v1/sih/*`) backed by 13 tables; the seeder fills
them with *honest starter content* (checklists, risks, Q&A, sourced references)
but **no fabricated metrics** — every observed/baseline/actual field is null
until real data is entered, and the readiness dashboard refuses to estimate.

## Where each rubric criterion lives

| Criterion | Page | Evidence API |
|---|---|---|
| Problem Fit | `/admin/research`, `/admin/problem-links`, `/admin/impact` | `/sih/research`, `/sih/problem-links`, `/sih/impact/computed` |
| Innovation | `/admin/innovation`, `/admin/competitors`, `/admin/prior-art`, `/admin/tech` | `/sih/innovation`, `/sih/competitors`, `/sih/prior-art`, `/sih/tech-scouting` |
| Feasibility | `/admin/risks`, `/demo` | `/sih/risks`, journey pytest suite |
| Tech Depth | `/docs` (OpenAPI), `/admin/sih-readiness` (test card) | `/sih/tests` (real JUnit artifact), `docs/SECURITY_AUDIT.md` |
| Presentation | `/demo`, `/admin/judge-qa`, `/admin/references` | `/sih/judge-questions`, `/sih/evidence-pack/export` |

Readiness rollup: **GET /api/v1/sih/readiness** → per-criterion completion
computed *only* from checklist statuses (Complete=100%, Partial=50%,
Pending=25%, Missing=0%). No other number is ever synthesized.

## Honesty invariants (enforced by tests)

- `test_competitor_matrix_honesty` — ≥45 of 65 competitor cells are
  NOT_EVALUATED; KARVANTANA's own `offline_first` is **NO**.
- `test_impact_computed_from_real_rows` — manual metric definitions have **no
  actual values**; computed values carry sample sizes and a dataset disclosure.
- `test_metric_observation_provenance` — a TARGET observation is stored as
  TARGET, never displayed as REAL.
- `test_risks_register_complete` — R-02 (offline) explicitly says "NOT yet
  shipped"; R-04 (hallucination) points to the verifiable approval audit.
- `test_prior_art_never_claims_absence` — no record may claim "no patent
  exists"; only performed searches are logged.

## Collecting real evidence (the intended workflow)

1. **Interviews/surveys** → `/admin/research` → "+ Record evidence"
   (respondent code, district/state only, consent status, pain points).
   Problem Fit's research checklist item flips MISSING → PARTIAL/COMPLETE
   based on what is actually entered.
2. **Measurements** (e.g., listing-creation minutes with a stopwatch) →
   `POST /api/v1/sih/problem-links` with `observed`, `sample_size`,
   `evidence_source` → the row's status flips to COMPLETE.
3. **Metric observations** → `POST /api/v1/sih/impact/{code}/observation`
   with `provenance: REAL|TARGET|SIMULATED|DEMO` — the dashboard displays the
   provenance badge beside the value.
4. **Competitor research** → `POST /api/v1/sih/competitors` per cell **with
   source URL**; unsourced updates stay PENDING_VALIDATION.
5. **Test refresh** → `python3 -m pytest tests/ --junitxml=test-results.xml`
   → `/admin/sih-readiness` shows the real counts.

## Demo protocol (deterministic, vendor-independent)

Open **`/demo`** for the guided 19-step script with logins per step. Demo
logins: `artisan1@karvantana.demo / artisan-demo-1` (artisan),
`anita@example.com / buyer-demo-1234` (buyer),
`orders@brightspaces.example.com / buyer-demo-1234` (B2B),
`admin@karvantana.demo / admin-demo-1234` (admin). Reseed anytime:
`python3 seed_demo.py && python3 seed_sih.py`.

## Current honest gaps (also visible in the dashboard)

- Zero real research records collected (instrument ready, data pending).
- No measured baselines/observed outcomes for the five problem mappings.
- Coverage % unmeasured; load benchmarks not run; pen-test not performed.
- Offline-first on web: NO (architecture documented; implementation Phase 2).
- Competitor matrix: only cells verifiable from official sites are sourced.
