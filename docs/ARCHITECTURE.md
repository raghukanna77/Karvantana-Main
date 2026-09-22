# KARVANTANA — Architecture Overview

Companion to `BLUEPRINT.md` (the full engineering contract). This file is the
**as-built** summary for evaluation; every claim maps to code.

## Layers

```
React 19 + TS SPA (Vite, 88 KB gzip)
  │  typed API client (core/api.ts) — the only network caller
  ▼
FastAPI (/api/v1) — versioned routers, Pydantic validation, RBAC guards
  │  services layer (business logic; no logic in routes)
  │  ├─ AI pipeline (ai/pipeline.py) → provider interfaces (ai/providers/*)
  │  ├─ order/payment/review/commerce services
  │  └─ analytics service (real computed dashboards)
  ▼
SQLAlchemy 2.0 ORM — dual target: SQLite (demo/tests) · PostgreSQL (prod path)
  ├─ 45+ tables: users, profiles, catalog, products, commerce, engagement,
  │              analytics, ai governance, SIH evidence (13 tables)
  └─ UUID PKs, timestamps, soft deletes, indexes, FK constraints
Media: local ./media (dev) → S3 + signed URLs (prod path)
```

## API surface (routers)
`auth`, `artisans`, `products`, `ai`, `orders`, `payments`, `commerce`
(bulk/custom/quotes), `analytics` (+admin/cluster/events/export),
`sih` (evidence). OpenAPI live at `/docs`.

## Cross-cutting
- **Errors:** structured `{error:{code,message,request_id}}` via central handlers.
- **Events:** in-process domain event bus (`core/events.py`).
- **Feature flags:** `core/feature_flags.py`.
- **Rate limiting:** per-user buckets on AI + analytics ingestion.
- **Observability:** request IDs, structured logging, `ai_usage` (latency,
  confidence, cost), audit logs.
- **Idempotency:** order creation keyed by `Idempotency-Key`.

## AI provider pattern (vendor-agnostic)
```
pipeline.py  →  SpeechProvider / TranslationProvider / VisionProvider /
                LLMProvider / EmbeddingProvider (interfaces in providers/base.py)
Demo providers are clearly labeled; production providers drop in via config
(settings.AI_PROVIDER). Generation consumes structured fields only; every
inference is audited (ai_generations) with confidence + human approval.
```

## Human-in-the-loop audit model
`ai_field_approvals` records per-field APPROVE/EDIT/REJECT/REGENERATE with the
verbatim AI output, final output, decider and timestamp — the acceptance-rate
metrics on `/admin/impact` are computed from these real rows.

## Testing
41 pytest tests (unit extraction/pricing + API auth + full journey + SIH
evidence). JUnit artifact at `backend/test-results.xml`; the readiness page
reads it live via `/api/v1/sih/tests` — coverage is displayed only when
actually measured (it currently is not).

## Deployment path
Stateless API behind a gateway; Postgres; S3 media; async AI jobs; per-request
cost tracking. Details: `docs/DEPLOYMENT.md`, docker-compose at repo root.
