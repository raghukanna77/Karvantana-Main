"""Live auth smoke test — exercises every auth endpoint against a running server.

Rate-limit aware: the auth scope allows 10 requests/min per IP, so on a 429 the
test waits `retry_after_seconds` and retries once. This keeps the run
deterministic regardless of other traffic from the same IP.

Usage: python scripts/auth_smoke_test.py [base_url]
Default base_url: http://localhost:8014  (pass http://localhost:5175 to test the proxy)
"""

from __future__ import annotations

import sys
import time
import uuid

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8014"
API = f"{BASE}/api/v1/auth"

results: list[tuple[str, bool, str]] = []
_client = httpx.Client(timeout=10)


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")


def post(path: str, json: dict) -> httpx.Response:
    """POST with one rate-limit-aware retry (waits out the sliding window)."""
    r = _client.post(f"{API}{path}", json=json)
    if r.status_code == 429:
        retry = r.json().get("error", {}).get("details", {}).get("retry_after_seconds", 61)
        print(f"      (rate limited — waiting {retry}s)")
        time.sleep(min(retry, 62) + 0.3)
        r = _client.post(f"{API}{path}", json=json)
    return r


def get(path: str, headers: dict | None = None) -> httpx.Response:
    return _client.get(f"{API}{path}", headers=headers)


def main() -> None:
    # 1. login: wrong password must give a uniform 401 (not reveal account existence)
    r = post("/login", {"email": "artisan1@karvantana.demo", "password": "wrong-pass"})
    check("login wrong password → 401 uniform", r.status_code == 401,
          f"HTTP {r.status_code} {r.json().get('error', {}).get('message', '')}")

    # 2. login: nonexistent account must match the same message
    r2 = post("/login", {"email": "nobody@x.io", "password": "wrong-pass"})
    same = r.json().get("error", {}).get("message") == r2.json().get("error", {}).get("message")
    check("login unknown email → same uniform message", r2.status_code == 401 and same)

    # 3. login: correct credentials
    r = post("/login", {"email": "artisan1@karvantana.demo", "password": "artisan-demo-1"})
    ok = r.status_code == 200 and "access_token" in r.json() and r.json().get("user", {}).get("role") == "ARTISAN"
    check("login correct credentials → 200 + tokens", ok, f"HTTP {r.status_code}")
    tokens = r.json()

    # 4. /me with access token
    r = get("/me", {"Authorization": f"Bearer {tokens['access_token']}"})
    check("GET /auth/me → 200", r.status_code == 200 and r.json().get("email") == "artisan1@karvantana.demo",
          f"HTTP {r.status_code}")

    # 5. /me without token must be 401
    r = get("/me")
    check("GET /auth/me no token → 401", r.status_code == 401, f"HTTP {r.status_code}")

    # 6. refresh rotation: old token must die after use
    r = post("/refresh", {"refresh_token": tokens["refresh_token"]})
    ok = r.status_code == 200 and "access_token" in r.json()
    check("refresh → 200 new pair", ok, f"HTTP {r.status_code}")
    r2 = post("/refresh", {"refresh_token": tokens["refresh_token"]})
    check("refresh reuse of rotated token → 401", r2.status_code == 401, f"HTTP {r2.status_code}")
    new_tokens = r.json()

    # 7. register: unique account
    email = f"smoke_{uuid.uuid4().hex[:8]}@example.com"
    r = post("/register", {"full_name": "Smoke Test", "email": email, "password": "smoke-pass-123", "role": "BUYER"})
    ok = r.status_code == 200 and r.json().get("user", {}).get("role") == "BUYER"
    check("register new account → 200", ok, f"HTTP {r.status_code} {r.text[:120]}")
    reg = r.json() if r.status_code == 200 else {}

    # 8. register: duplicate must 409
    r = post("/register", {"full_name": "Smoke Test", "email": email, "password": "smoke-pass-123", "role": "BUYER"})
    check("register duplicate → 409", r.status_code == 409, f"HTTP {r.status_code}")

    # 9. register: weak password must be rejected by schema validation
    r = post("/register", {"full_name": "Smoke Test", "email": f"x{uuid.uuid4().hex[:6]}@y.io", "password": "short", "role": "BUYER"})
    check("register weak password → rejected", r.status_code in (422, 400), f"HTTP {r.status_code}")

    # 10. login with the freshly registered account
    r = post("/login", {"email": email, "password": "smoke-pass-123"})
    check("login freshly registered account → 200", r.status_code == 200, f"HTTP {r.status_code}")

    # 11. OTP flow: request then verify (digit-only phone — uuid hex can contain a-f)
    phone = f"98765{uuid.uuid4().int % 100000:05d}"
    r = post("/otp/request", {"phone": phone})
    ok = r.status_code == 200 and r.json().get("demo_code")
    check("otp request → 200 + demo code", ok, f"HTTP {r.status_code} {r.text[:120]}")
    code = r.json().get("demo_code", "")
    r = post("/otp/verify", {"phone": phone, "code": code, "full_name": "OTP Smoke"})
    check("otp verify → 200 tokens", r.status_code == 200, f"HTTP {r.status_code} {r.text[:120]}")

    # 12. otp verify with wrong code → 401
    phone2 = f"98766{uuid.uuid4().int % 100000:05d}"
    post("/otp/request", {"phone": phone2})
    r = post("/otp/verify", {"phone": phone2, "code": "000000", "full_name": "OTP Smoke"})
    check("otp verify wrong code → 401", r.status_code == 401, f"HTTP {r.status_code}")

    # 13. logout revokes refresh token
    r = post("/logout", {"refresh_token": new_tokens["refresh_token"]})
    check("logout → 200", r.status_code == 200, f"HTTP {r.status_code}")
    r = post("/refresh", {"refresh_token": new_tokens["refresh_token"]})
    check("refresh after logout → 401", r.status_code == 401, f"HTTP {r.status_code}")

    # 14. edge cases: malformed email on login, bad phone on OTP request
    r = post("/login", {"email": "not-an-email", "password": "whatever123"})
    check("login malformed email → 401 (not crash)", r.status_code == 401, f"HTTP {r.status_code}")
    r = post("/otp/request", {"phone": "12"})
    check("otp request bad phone → 422", r.status_code == 422, f"HTTP {r.status_code}")

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} passed")
    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"total {time.time() - t0:.2f}s")
