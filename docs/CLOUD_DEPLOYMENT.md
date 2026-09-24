# KARVANTANA — Cloud Deployment Guide

Run the backend on a cheap cloud host with HTTPS so the Android app and the
website work from anywhere, not just on your home Wi-Fi.

This is the small, hands-on path (one VPS, one domain, Caddy for HTTPS).
For the full production blueprint (PostgreSQL, S3 media, containers, Alembic),
see `docs/DEPLOYMENT.md` — the settings are identical; this guide gets you
online first.

**What you need**

- A VPS: any small Linux box — Oracle Cloud free tier, Hetzner CX22, DigitalOcean
  droplet, AWS Lightsail ($5/mo tier), EC2 `t4.micro` free tier, etc. 1 GB RAM
  is enough (FastAPI + SQLite idle well under that).
- A domain name you control (e.g. `karvantana.example.com`). **HTTPS requires a
  domain** — Let's Encrypt does not issue certificates for bare IPs, and an IP
  also defeats the point: Android blocks cleartext to anything outside the
  private LAN ranges (see `android/…/network_security_config.xml`).
- SSH access to the box, and ~15 minutes.

---

## 1. Point DNS at the VPS

Create an **A record**: `api.example.com` → the VPS public IP. Verify:

```bash
dig +short api.example.com        # should print the VPS IP
```

Keep the TTL low (300s) until things work. One subdomain for the API is enough;
the Android app does not need a website to exist — it talks to the API directly.

## 2. Prepare the server

```bash
ssh root@VPS_IP

# System packages
apt update && apt -y upgrade
apt -y install python3-venv python3-pip git caddy ufw
# Debian/Ubuntu names; on RHEL-family use dnf equivalents.

# Dedicated user (don't run the app as root)
useradd -m -s /bin/bash karva
```

## 3. Get the code and configure

```bash
su - karva
git clone <your-repo-url> karvantana    # or scp/rsync a copy of the repo
cd karvantana/backend

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Create `.env` next to `app/` (i.e. `backend/.env`) — **these are the
production-critical settings**:

```bash
cat > .env <<'EOF'
ENV=production
DATABASE_URL=sqlite:///./karvantana.db
JWT_SECRET=<50+ random chars — see below>
CORS_ORIGINS=https://app.example.com,https://localhost
AI_PROVIDER=demo
PAYMENT_PROVIDER=demo
MEDIA_DIR=/home/karva/karvantana/backend/media
EOF
```

Generate a real secret (do **not** reuse the dev default — it also derives the
payment-webhook signature secret):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Notes on the settings:

- `ENV=production` matters: the app then skips auto `create_all`, so create the
  schema once with the seed script below (or Alembic, see `docs/DEPLOYMENT.md`).
  Keep it `production` — do not flip back to development on a live database.
- `CORS_ORIGINS`: add the origins that serve the **web frontend**, if you host
  one (`https://app.example.com`). The Android WebView's origin is
  `https://localhost` (Capacitor `androidScheme: "https"`), include it if you
  also test the app against this server from a browser context. Leave out the
  LAN dev URLs.
- SQLite (`karvantana.db` + `media/`) is fine to start. When you outgrow it,
  set `DATABASE_URL=postgresql+psycopg://…` — see `docs/DEPLOYMENT.md`.

## 4. Seed the schema (and demo data, if you want it)

Because `ENV=production` disables auto table creation, create the schema once:

```bash
.venv/bin/python seed_demo.py     # creates tables + clearly-labeled demo data
```

- `seed_demo.py` is idempotent (it skips if demo rows exist) and marks every
  record `is_demo=True`. It also prints the demo credentials. **Change or remove
  the demo accounts** before real users sign up, and never mix demo seeds with
  a production database (blueprint §134). If you don't want demo data, run the
  same script once and then delete the `is_demo=True` rows, or create your
  admin/user accounts via `POST /api/v1/auth/register` instead.
- The first admin user can self-register; promote them:

  ```bash
  .venv/bin/python - <<'EOF'
  from app.core.database import SessionLocal
  from app.models.user import User
  db = SessionLocal()
  u = db.query(User).filter(User.email == "you@example.com").one()
  u.role = "ADMIN"
  db.commit()
  EOF
  ```

## 5. Run the app as a service

Create `/etc/systemd/system/karvantana.service`:

```ini
[Unit]
Description=KARVANTANA API (uvicorn)
After=network.target

[Service]
User=karva
WorkingDirectory=/home/karva/karvantana/backend
ExecStart=/home/karva/karvantana/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8014
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now karvantana
systemctl status karvantana        # active (running)?
journalctl -u karvantana -f        # live logs
```

The app now listens on **127.0.0.1:8014 only** — the public never reaches it
except through Caddy. (If you must expose it, note `--host 0.0.0.0` is the LAN
mode from the README; on a VPS it means the open internet.)

## 6. HTTPS with Caddy (automatic Let's Encrypt)

Copy `deploy/Caddyfile` from the repo (shown below) and adjust the domain.
The reverse proxy must forward the raw request body — the payment webhook
verifies an HMAC over the exact bytes:

```
# /etc/caddy/Caddyfile
api.example.com {
    encode gzip
    reverse_proxy 127.0.0.1:8014
}
```

That's the whole file. Caddy obtains and renews the certificate automatically
(ports 80/443 must be open) and proxies to uvicorn without buffering away the
webhook signature.

```bash
systemctl reload caddy
curl -s https://api.example.com/api/health
# {"status":"ok","app":"KARVANTANA","env":"production",...}
```

Firewall — allow only web ports + SSH:

```bash
ufw allow OpenSSH
ufw allow 80,443/tcp
ufw enable
```

Optional: serve the web frontend from the same box by adding a second site
block (`app.example.com { root * /home/karva/frontend-dist; file_server; try_files {path} /index.html }`)
after building the frontend with `npm run build` and copying `dist/` up.

## 7. Point the Android app at the cloud server

Nothing to rebuild. The app stores the server address on-device; set it on the
Login screen:

1. Open the app → Login screen → **Server address** → enter
   `https://api.example.com` (no port, no trailing slash) → **Save**.
2. Sign in and confirm the marketplace loads and images render (images come
   from `/media/...` on the same origin, so they follow the server address).

HTTPS matters here, not just for security: with HTTPS the app also works on
cellular networks and avoids WebView cleartext restrictions entirely. The
`http://192.168.1.20:8014` LAN flow from the README keeps working for home
development — it is permitted by the Android network security config
(see `frontend/android/app/src/main/res/xml/network_security_config.xml`).

Checklist before you share the app with real users:

- [ ] `curl https://api.example.com/api/health` → `status: ok`
- [ ] Login works from the app **on cellular data** (Wi-Fi off)
- [ ] Product photo upload works (image upload + `/media` serving)
- [ ] Demo payment settles via the webhook (order → PAID) — this exercises the
      HTTPS reverse-proxy body-forwarding path
- [ ] HTTPS certificate is valid (padlock / `curl -vI https://api.example.com`)
- [ ] Demo accounts changed/removed; strong `JWT_SECRET` in `.env`

## 8. Upgrades, backups, costs

**Deploy an update**

```bash
ssh karva@VPS
cd ~/karvantana && git pull
cd backend && .venv/bin/pip install -r requirements.txt
systemctl restart karvantana
```

If the frontend is served from the box, rebuild it (`npm run build` locally,
rsync `dist/`) — no Android rebuild needed since the app reads the server
address at runtime.

**Back up** (cron: `crontab -e`)

```bash
#!/bin/sh
# SQLite backup (safe online snapshot) + media, keep 7 days
cd /home/karva/karvantana/backend
.venv/bin/python -c "import sqlite3,shutil; shutil.copyfile('karvantana.db','/var/backups/karvantana/karvantana-$(date +\%F).db')" || \
  cp karvantana.db /var/backups/karvantana/karvantana-$(date +\%F).db
tar czf /var/backups/karvantana/media-$(date +\%F).tgz media/
find /var/backups/karvantana -mtime +7 -delete
```

(Make the dir first: `mkdir -p /var/backups/karvantana`. For a transactionally
safe copy use `sqlite3 karvantana.db ".backup '/var/backups/…'"`.)

**Rough monthly cost**: $0 (Oracle/AWS free tier) to ~$5 (Hetzner/DigitalOcean
small VPS). The rate-limited AI endpoints (`RATE_LIMIT_AI_PER_MIN=12` default)
and paginated queries are the cost controls documented in `docs/DEPLOYMENT.md`;
the demo AI providers cost nothing.

## 9. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| App says "network error", works in browser | Address typed with trailing `/` or path — enter bare origin `https://api.example.com` |
| `curl: (60) certificate` / app TLS error | DNS not propagated or Caddy not reloaded — check `journalctl -u caddy`; ports 80/443 blocked |
| Health returns `env: development` | `.env` not loaded (must be `backend/.env`) or service not restarted |
| 403/CORS errors only in web frontend | Origin missing from `CORS_ORIGINS` (exact scheme + host) |
| Images 404 | `MEDIA_DIR` points elsewhere now — keep it stable or migrate `media/` with the DB |
| Webhook never settles orders | Proxy stripping the body — use the Caddyfile above; check `X-Signature` reaches the app |
| Rate-limited during demos | `RATE_LIMIT_AUTH_PER_MIN=10` / `RATE_LIMIT_AI_PER_MIN=12` per user — raise in `.env` for a demo event |

## 10. Beyond one box

- **PostgreSQL** when SQLite write contention shows: switch `DATABASE_URL`,
  restore from a dump; add Alembic migrations first (`docs/DEPLOYMENT.md`).
- **S3 media** via `STORAGE_BACKEND=s3` so media survives redeploys.
- **HTTPS webhook receiver for a real gateway**: point Razorpay's webhook at
  `https://api.example.com/api/v1/payments/webhook`; the signature-verified
  settle path is already the only way orders become PAID.
- **Hardening**: `fail2ban`, SSH keys only, unattended-upgrades. The app already
  sends `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and uses
  per-user rate limits — see `docs/SECURITY_AUDIT.md`.
