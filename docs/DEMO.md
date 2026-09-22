# KARVANTANA — Demo Protocol (SIH Presentation)

## Golden rule
The demo runs entirely on **labeled demo data** and **demo providers**. No
external vendor is required. Fallback data is shown as "Demo fallback data" —
never presented as live AI output.

## Guided walkthrough
Open **`/demo`** in the app — it is the 19-step script (login → capture →
voice → AI catalogue → confidence → approval → pricing → publish → buyer
discovery → order → B2B quote → review/follow → reorder → dashboard insights)
with per-step logins and an inline progress tracker.

## Demo logins
| Role | Email | Password |
|---|---|---|
| Artisan (Priya) | `artisan1@karvantana.demo` | `artisan-demo-1` |
| Buyer (Anita) | `anita@example.com` | `buyer-demo-1234` |
| B2B (BrightSpaces) | `orders@brightspaces.example.com` | `buyer-demo-1234` |
| Admin | `admin@karvantana.demo` | `admin-demo-1234` |
| Cluster manager | `cluster@karvantana.demo` | `cluster-demo-1234` |

## Reset to a known state (deterministic)
```bash
cd backend
rm -f karvantana.db
python3 seed_demo.py     # marketplace + orders + reviews (all users labeled DEMO)
python3 seed_sih.py      # evidence: checklist, risks, Q&A, matrix (idempotent)
```

## Running
- Web: `cd frontend && npm run dev` → http://localhost:5175 (Vite proxies /api)
- API: `cd backend && python3 -m uvicorn app.main:app --port 8014`
- Full machine notes (Rosetta/launchd quirks included): `../../.freebuff/run.md`

## Backup plan (if the live demo machine dies)
1. **Backup video/screenshot set** — capture the 19 steps once before the event
   (TODO before presentation day; currently NOT recorded — honest gap).
2. **Static fallback** — `GET /api/v1/sih/evidence-pack/export` (Markdown) can
   be pre-downloaded and presented without any server.
3. **Presenter scripting** — `/admin/judge-qa` contains prepared answers; the
   competitor matrix's NOT_EVALUATED cells demonstrate research discipline.

## Judge-proof moments (things you can show live, verifiably)
- Human-in-the-loop: reject a catalogue field, then show it in
  `ai_field_approvals` (admin impact page reflects acceptance counts).
- Payment security: complete checkout, show the order only became CONFIRMED
  after the server verified the webhook signature.
- Honesty: show `/admin/competitors` NOT_EVALUATED cells and the readiness
  page's "MISSING" research item next to the empty research list.
