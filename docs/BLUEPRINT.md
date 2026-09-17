# KARVANTANA — Engineering Blueprint

> **From Craft to Commerce** · AI-Powered Digital Business Manager for Marginalized Artisans
> "We don't just put artisans online. We make them digitally commerce-ready."

This blueprint is the engineering contract for the repository. Implementation follows it
milestone by milestone. The non-negotiable end-to-end journey:

```
Artisan → Product Capture → Voice → AI Catalogue → Pricing → Publish →
Buyer → Order → Delivery → Review → Reputation → Repeat Order → Business Insight
```

---

## 1. Repository Structure

```
karvantana/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app factory, middleware, routers, OpenAPI
│   │   ├── core/                 # config, logging, errors, events, feature flags
│   │   ├── security/             # jwt, passwords, rbac, dependencies, rate limiting
│   │   ├── models/               # SQLAlchemy ORM (full schema, UUID PKs, timestamps)
│   │   ├── schemas/              # Pydantic request/response DTOs
│   │   ├── repositories/         # data access (service ↔ repository separation)
│   │   ├── services/             # business logic (orders, pricing, ai orchestration…)
│   │   ├── ai/                   # AI pipeline + provider interfaces
│   │   │   ├── providers/        # llm, speech, translation, vision, embeddings
│   │   │   ├── pipeline.py       # validate → preprocess → infer → structure → confidence
│   │   │   ├── prompts.py        # prompt registry (versioned, auditable)
│   │   │   ├── confidence.py     # value/confidence/source model
│   │   │   └── assistant.py      # tool-calling business assistant
│   │   ├── integrations/         # payment, logistics, notifications, commerce networks
│   │   │   └── providers/        # Razorpay-shaped + Demo (clearly labeled) providers
│   │   ├── analytics/            # event tracking, demand intelligence, KPIs
│   │   ├── workers/              # async job queue abstraction (in-proc / future Celery)
│   │   └── api/
│   │       └── v1/               # versioned routers
│   ├── tests/                    # pytest: unit + integration + API
│   ├── prompts/                  # versioned prompt files (catalogue_generator_v1 …)
│   ├── requirements.txt
│   ├── seed_demo.py              # clearly-labeled demo data
│   └── Dockerfile
├── frontend/                     # React 18 + TypeScript strict + Vite
│   └── src/
│       ├── core/                 # config, api client, types, errors
│       ├── design/               # design system: KButton, KCard, KVoiceButton …
│       ├── i18n/                 # 10-language architecture, translation keys
│       ├── routing/              # router + role guards
│       ├── state/                # auth state, offline queue, notifications
│       ├── features/             # landing, auth, artisan, products, ai-catalogue,
│       │                         # pricing, marketplace, buyer, orders, bulk, b2b,
│       │                         # insights, admin, clusters, notifications
│       └── styles/               # theme tokens, craft motifs
├── docs/                         # BLUEPRINT, ARCHITECTURE, API, DATABASE, AI, SECURITY,
│                                 # DEPLOYMENT, TESTING, DEMO
├── scripts/                      # dev.sh, seed, install
├── .github/workflows/ci.yml      # lint → typecheck → tests → build
├── docker-compose.yml            # optional: postgres, redis, backend, frontend
└── .env.example
```

## 2. Frontend Architecture

- **React 18 + TypeScript strict + Vite.** Artisan experience is mobile-first; admin/B2B
  dashboards responsive desktop-first.
- **State:** lightweight stores (auth session, offline queue, cart) — no network calls in
  widgets/components; all data flows through `core/api`.
- **Design system:** deep navy `#0A1628` / charcoal foundation, electric blue `#2E6BFF`,
  violet `#7C5CFF` accents, glass surfaces, Indian craft-inspired motifs (subtle weave/loom
  geometry). Components: `KButton, KCard, KInput, KVoiceButton, KImageUploader,
  KProductCard, KArtisanCard, KPriceRecommendation, KConfidenceBadge, KOrderStatus,
  KRating, KBottomSheet, KAIInsight, KEmptyState, KErrorState, KLoadingState`.
- **i18n:** `t(key)` lookup over JSON catalogs; 10 languages seeded (English, Tamil, Hindi,
  Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi). Never hard-code UI
  strings in features.
- **Offline-first:** localStorage-backed draft products, voice notes and mutation queue;
  sync banner `Offline Mode — N changes waiting to sync`; replay on reconnect with conflict
  rule *server-wins for published entities, client-wins for drafts*.
- **Navigation:** role-aware.
  - Artisan bottom nav: `Home · Products · Orders · Insights · Profile` + `+ Add Product` FAB + `Ask KARVANTANA`.
  - Buyer: `Home · Explore · Orders · Saved · Profile`.
  - B2B: `Dashboard · Discover · Requests · Orders · Profile`.
  - Admin desktop sidebar: `Overview · Artisans · Products · Orders · AI · Analytics · Clusters · Settings · Audit`.

## 3. Backend Architecture

- **FastAPI + SQLAlchemy 2 + Pydantic v2.** Service ↔ repository separation; no business
  logic in route handlers. SQLite for zero-config local dev; PostgreSQL for staging/prod
  (SQLAlchemy URL swap, UUID stored as `CHAR(36)` for portability).
- **Auth:** JWT access (30 min) + refresh (14 d, rotating), bcrypt hashes, mobile OTP
  (demo delivery) + email/password, role guards `ARTISAN, BUYER, B2B_BUYER,
  CLUSTER_MANAGER, ADMIN`, resource-ownership dependencies, audit logging.
- **Structured errors** (`error.code/message/request_id`), request IDs, structured JSON
  logs, CORS + security headers, per-scope rate limiting.

## 4. Database ERD (core)

```
users ─┬─< artisan_profiles ─< artisan_languages
       ├─< buyer_profiles ──< business_profiles
       └─< otp_codes / refresh_tokens / consents

artisan_profiles ─< products ─┬─< product_images
                              ├─< product_attributes   (value/confidence/source)
                              └─< product_variants / inventory fields

categories ─< products   craft_types ─< artisan_profiles   materials ─< products

products ─< pricing_recommendations ─< pricing_history
products ─< ai_generations (input, provider, model, prompt_version, output, confidence, approved_by)
voice_transcripts ─< products (language, original, translated)

users(buyer) ─< orders ─< order_items ─> products
orders ─< order_status_history ─< payments ─< refunds
orders ─< shipments ─< tracking_events

bulk_requests ─< quotes ─< order (fulfilment path)
custom_requests ─< quotes
users(buyer) ─< reviews ─> products / artisans (verified purchases only)

users ─< follows >─ artisan_profiles      users ─< saved_artisans / saved_products
artisan_clusters ─< cluster_members       cluster_managers ─< artisan_clusters

analytics_events (actor, event_type, entity, payload)   demand_signals
notifications   messages   disputes   audit_logs   ai_usage
```

Constraints: UUID PKs, `created_at/updated_at`, soft-delete (`deleted_at`) on catalog and
profiles, FK indexes, unique constraints (e.g. one review per order item, one follow per
user/artisan), optimistic locking on inventory decrement, transactional order creation.

## 5. API Specification (v1, `/api/v1`)

| Area | Endpoints |
|---|---|
| auth | `POST /auth/otp/request`, `POST /auth/otp/verify`, `POST /auth/login`, `POST /auth/register`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me` |
| artisans | `GET /artisans` (filters), `GET /artisans/{id}` (public profile), `PATCH /artisans/me` |
| products | `GET /products` (search/filters), `GET /products/{id}`, `POST /products`, `PATCH /products/{id}`, `POST /products/{id}/publish`, `DELETE /products/{id}` |
| ai | `POST /ai/transcribe`, `POST /ai/catalogue/generate`, `POST /ai/catalogue/regenerate-field`, `POST /ai/pricing/recommend`, `POST /ai/image/enhance`, `POST /ai/assistant/query` (tool-calling) |
| orders | `POST /orders` (idempotency key), `GET /orders`, `PATCH /orders/{id}/status` (artisan transitions) |
| payments | `POST /payments/create-intent`, `POST /payments/webhook` (signature-verified, idempotent), `POST /payments/refund` |
| reviews | `POST /products/{id}/reviews` (verified orders only) |
| bulk / custom | `POST /bulk-requests`, `POST /bulk-requests/{id}/quotes`, `POST /bulk-requests/{id}/accept`, `POST /custom-requests`, same quote flow |
| relationship | `POST /artisans/{id}/follow`, `DELETE …/follow`, `POST /artisans/{id}/save`, `POST /products/{id}/save`, `POST /orders/{id}/reorder` |
| analytics | `GET /analytics/artisan/dashboard`, `GET /analytics/admin/overview`, `GET /analytics/impact` |
| admin | `GET/POST /admin/artisans/{id}/verify`, `PATCH /admin/products/{id}/moderate`, `GET /admin/ai/monitoring`, `GET /admin/audit-logs` |
| clusters | `GET /clusters/me`, `POST /clusters/{id}/artisans` (onboard), `GET /clusters/{id}/analytics` |
| notifications | `GET /notifications`, `PATCH /notifications/{id}/read` |
| events | `POST /events` (client analytics ingestion, rate-limited) |

Conventions: pagination (`?page=&page_size=`), filtering, structured errors with
`request_id`, `Idempotency-Key` header on mutating commerce endpoints.

## 6. Authentication / RBAC Model

- Roles: `ARTISAN`, `BUYER`, `B2B_BUYER`, `CLUSTER_MANAGER`, `ADMIN`. Role switches are
  admin-controlled; normal users never see role management.
- Guards: `require_authenticated`, `require_roles(...)`, `require_ownership(model_field)`
  dependencies; every non-public query is filtered by owner/visibility.
- Audit log rows for auth events, moderation, AI approvals, order transitions.

## 7. AI Architecture (provider-agnostic)

```
AIProvider interfaces:  LLMProvider · SpeechProvider · TranslationProvider
                        VisionProvider · EmbeddingProvider · RecommendationProvider
Implementations:        DemoAIProvider (deterministic, rule/heuristic based, labeled DEMO)
                        (real vendors plug in via env keys — OpenAI/GCP/Azure shapes)
```

- **Pipeline:** input validation → preprocessing → provider inference → schema-validated
  structured output → confidence tagging → human review → persistence. Raw LLM responses
  are never production data.
- **Confidence model:** every extracted field `{value, confidence, source}` with sources
  `VOICE | IMAGE | ARTISAN_INPUT | AI_INFERENCE | SYSTEM`. Low confidence renders
  "AI is not certain about this detail. Please confirm."
- **Prompt registry:** versioned prompt files (`catalogue_generator_v1`, `pricing_explainer_v1`,
  `buyer_requirement_parser_v1`, `business_assistant_v1`); every generation stores
  prompt_version + provider + model + latency for auditability.
- **Fallback:** provider chain with graceful degradation — manual catalogue creation always
  available; AI failure never blocks commerce.
- **Assistant:** intent detection → authorization → **tool calling** (dashboard queries,
  order lookups, inventory) — the LLM never sees the database directly and cannot mutate
  anything without an explicit confirmation step. Hallucination guard: answers only from
  tool-returned data; otherwise says "No data available yet."
- **Prompt-injection defense:** user transcripts/descriptions are untrusted data, never
  concatenated into system prompts; strict output schemas; tool allow-lists.

## 8. Offline Synchronization

Client queue of serialized mutations (draft product, transcript, field edits) with ids and
timestamps → replay on reconnect → per-entity conflict policy (drafts client-wins,
published server-wins) → sync status UI. Server stays authoritative for money & orders.

## 9. Payment Architecture

```
PaymentProvider interface: create_intent · verify_webhook · refund
 ├── DemoPaymentProvider (sandbox; clearly labeled; deterministic success/failure)
 └── RazorpayProvider (signature verification, key from env)
```
Server-side verification only — webhook validates signature + idempotency key before
transitioning order state; client "success" is never trusted. Refunds modeled in `refunds`.

## 10. Notification Architecture

`NotificationService` with channel adapters (`in_app`, `email`, `sms`, `whatsapp` demo
adapters). Events: order received, payment received, shipment, review, enquiry, bulk
request, AI catalogue ready, sync completed. In-app notification centre with deep links.

## 11. Commerce Network Integration

`CommerceNetworkAdapter` interface with `DemoCommerceAdapter` (labeled) and a
`CatalogueExporter` producing canonical JSON/CSV for ONDC/IndiaHandmade-shaped
destinations. No fake claims of live ONDC connectivity; the platform generates a
standardized catalogue ready for adaptation.

## 12. Deployment Architecture

- Dev: `scripts/dev.sh` (backend :8000, frontend :5173, SQLite, demo providers).
- Optional `docker-compose.yml`: postgres, redis, backend, frontend.
- Staging/prod: FastAPI in containers (ECS/Fargate-ready), PostgreSQL (RDS), S3 for media
  (signed URLs), Redis for cache/queue, CloudWatch/OTel observability, secret manager.
- Migrations via Alembic-style versioned tooling; backups + RPO/RTO documented in DEPLOYMENT.

## 13. Security Architecture

JWT + bcrypt; RBAC + ownership; rate limiting per scope; request validation; CORS allow-list;
security headers; upload validation (MIME/size/dimensions) with signed URLs; secrets only via
env; payment webhook signature verification; idempotency keys; audit logs; privacy by default
(no public phone numbers/addresses; buyer PII never exposed to artisans beyond order needs).

## 14. Testing Strategy

- **Unit:** pricing model, requirement parser, attribute extraction heuristics, RBAC,
  confidence logic, order state machine.
- **Integration/API (pytest + httpx):** auth flows, product lifecycle, order creation with
  inventory concurrency, payment webhook idempotency, quote acceptance, review gating,
  assistant tool authorization.
- **E2E (documented scripted demo):** the critical journey from capture → repeat order.

## 15. CI/CD Strategy

GitHub Actions: install → ruff lint → pytest → frontend typecheck/lint/build → backend
smoke boot. Environments: development / staging / production with env-var contracts.

## 16. Development Milestones

M1 Foundation (repo, design system, auth, DB, RBAC, API skeleton) → M2 Artisan
onboarding/profile → M3 AI capture + image studio → M4 Voice→translation→catalogue →
M5 Smart pricing → M6 Marketplace/search/profiles → M7 Cart/checkout/orders/payments →
M8 Bulk/custom commerce → M9 Reputation/repeat → M10 Analytics/demand → M11 AI assistant →
M12 Admin/clusters → M13 Notifications → M14 Commerce adapters → M15 Security →
M16 Testing/perf → M17 CI/CD → M18 Production audit.

**Implementation control:** every milestone goes PLAN → BUILD → CONNECT → VALIDATE →
REVIEW → REPORT with honest status (`COMPLETED / PARTIALLY COMPLETED / BLOCKED`).
Deep functionality beats screen count; nothing is presented as live integration unless it is.
