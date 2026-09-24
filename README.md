# KARVANTANA - From Craft to Commerce

**AI-Powered Digital Business Manager for Marginalized Artisans.**
KARVANTANA turns a photo and a voice note in the artisan's own language into a professional,
multilingual product listing with smart pricing — then connects that listing to consumers,
B2B buyers and institutions, and turns transactions into repeat buyer–artisan relationships.

> Marketplaces connect buyers to products. KARVANTANA connects buyers back to the artisan.

---

## Quick start

```bash
# Backend (Python 3.9+, FastAPI, SQLAlchemy)
cd backend
pip3 install -r requirements.txt
python3 seed_demo.py            # creates karvantana.db + demo media (clearly labeled DEMO)
python3 -m uvicorn app.main:app --port 8014

# Frontend (Node 18+, Vite + React + TS strict)
cd frontend
npm install
npm run dev                     # http://localhost:5175 (proxies /api → :8014)

# Tests
cd backend && python3 -m pytest tests/ -q   # 21 unit + integration tests
cd frontend && npx tsc --noEmit && npm run build
```

---

## Android app (Android Studio / Capacitor)

The Android app is a native shell around the same web build (Capacitor 6).

**One-time setup**
```bash
cd frontend
npm install                  # installs @capacitor/*
npm run android:sync         # builds web + copies into android/
npm run android:open         # opens the project in Android Studio
```
Then in Android Studio: **Build → Build Bundle(s)/APK(s) → Build APK(s)**
(or run on a device/emulator with the green ▶ button).

> Requires Android Studio with its bundled JDK 21 (Gradle 8.7 is configured via
> the wrapper, so no extra Java setup). After **any** frontend change, re-run
> `npm run android:sync` before rebuilding the APK — the web bundle inside
> `android/app/src/main/assets/public` is not tracked in git.

**Pointing the phone at your backend**
The app talks to the KARVANTANA server over your network:
1. Find your computer's LAN IP (`ipconfig` / `ifconfig`), e.g. `192.168.1.20`.
2. Run the backend with `python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8014`.
3. On the app's Login screen, set **Server address** to `http://192.168.1.20:8014` and Save.
   (The address is stored on the device; production deployments serve HTTPS and don't need it.)

> Phone and computer must be on the same Wi-Fi network. LAN cleartext HTTP is
> enabled app-wide for development (`android:allowMixedContent` + the network
> security config's base config); production servers use HTTPS — see
> [docs/CLOUD_DEPLOYMENT.md](docs/CLOUD_DEPLOYMENT.md).

> The web build inside `android/app/src/main/assets/public` is refreshed by
> `npm run android:sync` after any frontend change.

**Outside the home network?** Run the backend on a cheap cloud VPS with HTTPS
and point the app's Server address at it — see **[docs/CLOUD_DEPLOYMENT.md](docs/CLOUD_DEPLOYMENT.md)**.
No app rebuild needed; the address is read at runtime.

### Demo credentials (seeded, fictional)

| Role | Login | Password |
|---|---|---|
| Artisan (Priya, Tamil Nadu handloom) | `artisan1@karvantana.demo` | `artisan-demo-1` |
| Buyer | `anita@example.com` | `buyer-demo-1234` |
| B2B buyer | `orders@brightspaces.example.com` | `buyer-demo-1234` |
| Admin | `admin@karvantana.demo` | `admin-demo-1234` |

The seed script prints all logins and labels every record as **demo data**. Never mix demo
seeds with a production database (blueprint §134).

## The critical journey (verified end-to-end)

```
Artisan → Photo → Voice (Tamil) → AI extraction (per-field confidence + source)
        → AI catalogue (artisan-approved, per-field regenerate)
        → Smart pricing (cost + market range + "Why this price?")
        → Publish → Buyer discovers → Order (idempotent)
        → Server-verified demo payment → Fulfilment
        → Review (verified purchase) → Follow/Save → Reorder
        → Business insight (AI assistant over real data)
```

Also fully working: B2B bulk pipeline (plain-language requirement → AI parse → explainable
matching → artisan quote → accept → payable order at the quoted price), custom requests,
notifications, admin console (platform overview, moderation queue, AI governance, audit),
and cluster-manager dashboards.

## Architecture

```
karvantana/
├── docs/BLUEPRINT.md          # Engineering contract: ERD, API spec, AI/security/deployment
├── backend/                   # FastAPI + SQLAlchemy (SQLite dev / PostgreSQL prod)
│   └── app/
│       ├── api/v1/            # Thin routers: auth, artisans, products, ai, orders,
│       │                      #   payments, commerce (reviews/bulk/custom/quotes/notifications),
│       │                      #   analytics (incl. admin + clusters + canonical export)
│       ├── core/              # Config, structured errors, JSON logging, event bus, flags, db
│       ├── models/            # 41 normalized tables (UUID pk, timestamps, indexes, FKs)
│       ├── schemas/           # Pydantic request/response contracts
│       ├── services/          # Business logic (orders, payments, pricing, matching…)
│       ├── security/          # bcrypt, JWT access+refresh, RBAC, rate limits, ownership
│       └── ai/                # Provider-agnostic AI layer (blueprint §44)
│           ├── pipeline.py    # Validation → inference → confidence → persistence
│           ├── assistant.py   # Tool-calling business assistant (no free-form DB access)
│           └── providers/     # Demo LLM/speech/translation/vision + real slots
└── frontend/                  # React 18 + Vite + TS strict + Zustand
    └── src/
        ├── design/            # KButton/KCard/KConfidence/KAIStages… design system
        ├── features/          # artisan · marketplace · buyer · b2b · admin · cluster ·
        │                      # assistant · notifications · auth · landing
        ├── core/              # Typed API client + shared types
        ├── state/             # Zustand stores (auth session, offline queue, language)
        └── i18n/              # 10-language architecture, graceful fallback
```

## Honesty rules (enforced in code, not just documentation)

- **Payments**: the client "success" is never trusted. Orders settle only through the
  signature-verified webhook path (`payments/webhook`); the demo provider signs exactly as
  a real gateway would and is labeled **Demo — sandbox** in the UI.
- **AI**: every extracted field carries `value / confidence / source` (VOICE, IMAGE,
  AI_INFERENCE, ARTISAN_INPUT). Low-confidence fields ask the artisan to confirm; nothing
  publishes without approval. The assistant answers only from tool results over the
  artisan's own data, with sources shown.
- **Numbers**: dashboards, reputation and impact metrics are computed from real records —
  empty state says "No data yet", never a fabricated figure.
- **Integrations**: Razorpay/ONDC/WhatsApp are provider interfaces with clearly-labeled
  demo implementations; the canonical catalogue export (`/analytics/export/catalogue`)
  is the integration surface.

## Configuration

Copy `.env.example` → `.env` (see `docs/BLUEPRINT.md` §89). Key settings: `DATABASE_URL`
(SQLite default, PostgreSQL-ready), `JWT_SECRET`, `PAYMENT_PROVIDER=demo|razorpay`,
feature flags (`AI_ASSISTANT`, `B2B`, `ONDC`, …).

## Documentation

- `docs/BLUEPRINT.md` — repository structure, ERD, API specification, RBAC model,
  AI architecture, offline sync, payment/notification/commerce-network architecture,
  deployment, security, testing strategy, milestones.
- `docs/DEPLOYMENT.md` — environment variables and the production path
  (PostgreSQL, S3 media, containers, migrations).
- `docs/CLOUD_DEPLOYMENT.md` — hands-on guide: backend on a cheap cloud VPS
  with HTTPS so the Android app works outside the home network.
- API reference: FastAPI OpenAPI at `/docs` on the backend port.
