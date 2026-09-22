# KARVANTANA — Security & Privacy Audit (SIH Tech Depth evidence)

Status: **self-audit of the implemented build** (verifiable in code, paths
below). An external penetration test has **not** been performed — listed as a
gap, not checked off.

## Authentication & sessions
- bcrypt password hashing (`app/security/passwords.py`), constant-time verify.
- JWT access tokens with expiry + per-app secret (`app/security/jwt.py`);
  secret supplied via environment, never in the frontend bundle.
- OTP login path issues the same token machinery (`api/v1/auth.py`).
- **Gap:** refresh-token rotation and revocation list are not implemented
  (single short-lived access token today).

## Authorization (RBAC + ownership)
- `require_roles()` guard on **every** router (`app/security/dependencies.py`);
  admin/self-serve role escalation impossible (registration is role-fixed;
  admin provisioned internally — see `tests/conftest.py` admin fixture).
- Ownership checks live in services, not routes: `get_owned_product`,
  artisan-profile scoping on dashboard/analytics, order visibility limited to
  buyer/artisan/admin (`api/v1/orders.py`).
- Verified by tests: buyer → `/api/v1/sih/*` = 403; unauthenticated = 401.

## Input validation & uploads
- Pydantic schemas on every write endpoint (422 on violation).
- Upload validation: MIME sniffing, extension allow-list, size cap
  (`services/media_service.py` + product image endpoint).
- SIH research schema **rejects free-text PII by design**: respondent codes
  only; district/state level locations (`schemas/sih.py`).

## Rate limiting & abuse
- Per-user bucket `enforce("ai", user.id)` on AI endpoints; global limiter in
  `security/rate_limit.py`. Client analytics ingestion is allow-listed +
  rate-limited (`api/v1/analytics.py::events`).

## Payments (never trust the client)
- Order creation is idempotent (Idempotency-Key header, exposed via CORS).
- Settlement happens **only** on server-verified webhook signature
  (`services/payment_service.py`); the demo provider signs exactly like a real
  gateway, so the verification code path is identical for production.
- Double-payment / replay guarded by payment state machine + unique
  transaction constraints (`models/commerce.py`).

## Transport & headers
- Every response: `X-Request-ID`, `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`
  (`app/main.py`). CORS allow-list from settings.
- **Gap:** TLS termination is a deployment concern (documented in
  `docs/DEPLOYMENT.md`), enforced in the reference cloud config, not in app code.

## Audit & observability
- `audit_logs` table records consequential actions; AI requests recorded in
  `ai_generations` (input, model, confidence, approval, corrections) and
  `ai_usage` (latency, cost estimate) — queryable admin monitoring.

## Privacy & data minimization
- Artisan public profiles expose display name, craft, region — **not** phone,
  address, or bank data. Buyer contact is not exposed to artisans by serializers.
- Research module: anonymized IDs, consent status per record, no free-text
  identity fields.
- **Gap:** self-serve data-export/deletion UX is not yet built (soft-delete
  schema support exists).

## Secrets
- Settings via environment only (`core/config.py`); `.env.example` documents
  required variables; no secret values are committed; the frontend contains
  only the API base path.

## Summary table

| Control | Status | Where |
|---|---|---|
| Password hashing (bcrypt) | ✅ | security/passwords.py |
| JWT + expiry | ✅ | security/jwt.py |
| RBAC on all routers | ✅ | security/dependencies.py |
| Ownership checks | ✅ | services/* |
| Request validation | ✅ | schemas/* |
| Upload validation | ✅ | services/media_service.py |
| Rate limiting | ✅ | security/rate_limit.py |
| Security headers | ✅ | app/main.py |
| Audit logging | ✅ | models/analytics.py (AuditLog) |
| Server-verified payments | ✅ | services/payment_service.py |
| Data minimization (research) | ✅ | schemas/sih.py |
| Refresh-token rotation | ❌ planned | — |
| External penetration test | ❌ not performed | — |
| Data export/deletion UX | ❌ planned | schema support exists |
