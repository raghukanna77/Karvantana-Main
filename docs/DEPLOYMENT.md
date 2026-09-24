# KARVANTANA — Deployment Guide

## Environment variables (all optional in dev; required in production)

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy URL; `sqlite:///…` dev, PostgreSQL prod | `sqlite:///karvantana.db` |
| `JWT_SECRET` | Token signing secret (use a secret manager in prod) | dev default |
| `MEDIA_DIR` | Local media dir (dev) | `./media` |
| `AI_PROVIDER` | `demo` today; real providers via the same interface | `demo` |
| `PAYMENT_PROVIDER` | `demo` (signs like a real gateway) / Razorpay adapter | `demo` |
| `LOGISTICS_PROVIDER` | `demo` / future courier adapters | `demo` |
| `ENV` | `development` / `production` (production disables `create_all`) | `development` |
| `KARVANTANA_PORT` | Launcher convenience for the API port | — |

See `backend/app/core/config.py` for the full list; `.env.example` documents them.
**Never commit secret values** — the run docs record procedures, not secrets.

## Local (this repo, verified)
```bash
cd backend && python3 seed_demo.py && python3 seed_sih.py
python3 -m uvicorn app.main:app --port 8014
cd ../frontend && npm run dev   # http://localhost:5175, proxies /api → :8014
```
macOS note: the machine's user-level Python has an x86_64 pydantic wheel —
run under Rosetta (`arch -x86_64 /usr/bin/python3 …`) or install arm64 Python.

For the minimal hands-on path (single VPS, HTTPS via Caddy, Android app pointed
at the cloud server), see **[CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md)** with
ready-made configs in `deploy/` (Caddyfile + systemd unit).

## Production path (blueprint §55, not yet exercised at scale)
1. **Database:** PostgreSQL (`DATABASE_URL=postgresql+psycopg://…`). The ORM is
   dual-target; switch is configuration. Add Alembic before first prod migration.
2. **Media:** S3 bucket + signed URLs (media service interface already abstracts
   storage; local dir is the dev backend).
3. **App:** containerize (docker-compose at repo root); run behind a TLS
   terminating gateway; scale horizontally (stateless API).
4. **Migrations:** `ENV=production` disables auto `create_all` by design.
5. **AI/keys:** inject provider credentials via environment/secret manager;
   the demo providers remain for staging determinism.

## Cost & scale controls (implemented)
- Per-request AI usage rows (task, latency, confidence, est. cost) → admin
  monitoring is the budget dashboard.
- Per-user rate limiting on AI endpoints and analytics ingestion.
- Small client bundle; pagination on marketplace queries; DB indexes on hot
  filters (status, created_at, artisan_id).

## Load benchmark status
Not yet run — `/admin/sih-readiness` shows performance as PENDING VALIDATION
rather than inventing numbers.
