"""Live model accuracy & efficiency report from a running KARVANTANA server.

Measures the demo AI pipeline end-to-end: voice → translation → structured
extraction. Accuracy is reported as per-field confidence (the pipeline's own
accuracy signal); efficiency as measured wall-clock latency per stage.
"""

from __future__ import annotations

import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8014"
API = f"{BASE}/api/v1"

TAMIL_SAMPLE = "இது கைத்தறியில் நெய்த பருத்தி சேலை. இயற்கை நிறம் பயன்படுத்தியிருக்கோம். இதை நாலு நாள்ல தயாரிக்க முடியும்."


def login(c: httpx.Client, email: str, password: str) -> dict:
    r = c.post(f"{API}/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def main() -> None:
    c = httpx.Client(timeout=30)

    # ---- AI pipeline: voice → translate → extract --------------------------
    artisan = login(c, "artisan1@karvantana.demo", "artisan-demo-1")
    t0 = time.perf_counter()
    r = c.post(f"{API}/ai/voice/transcribe", headers=artisan,
               json={"text": TAMIL_SAMPLE, "language_hint": "ta"})
    wall_ms = (time.perf_counter() - t0) * 1000
    if r.status_code != 200:
        print(f"voice/transcribe failed: HTTP {r.status_code} {r.text[:200]}")
        sys.exit(1)
    data = r.json()

    print("=== AI PIPELINE — LIVE RUN (Tamil voice sample) ===")
    print(f"detected language : {data['language']}   (input hint: ta)")
    print(f"transcript        : {data['transcript'][:60]}…")
    print(f"transcript conf   : {data['confidence']:.2f}  (speech layer)")
    print(f"translated (en)   : {data['translated'][:60]}…")
    print()
    print(f"{'field':<18}{'value':<28}{'confidence':<12}source")
    for k, v in data["extracted"].items():
        print(f"{k:<18}{str(v['value'])[:26]:<28}{v['confidence']:<12.2f}{v['source']}")
    confs = [v["confidence"] for v in data["extracted"].values()]
    print()
    print(f"fields extracted  : {len(confs)}")
    print(f"mean confidence   : {sum(confs) / len(confs):.2f}  (accuracy signal; <0.75 → artisan asked to confirm)")
    print(f"pipeline latency  : {wall_ms:.0f} ms wall-clock (incl. HTTP)")

    # ---- buyer requirement parsing (B2B NLP) --------------------------------
    t0 = time.perf_counter()
    r = c.post(f"{API}/ai/requirements/parse", headers=artisan,
               json={"text": "We need 100 bamboo gift baskets under Rs 500 each for a corporate event, with our logo, in 30 days."})
    parse_ms = (time.perf_counter() - t0) * 1000
    if r.status_code == 200:
        p = r.json()
        print()
        print("=== B2B REQUIREMENT PARSER — LIVE RUN ===")
        print(f"parsed : quantity={p.get('quantity')} max_unit_price={p.get('max_unit_price')} "
              f"delivery_days={p.get('delivery_days')} category={p.get('category')} "
              f"customization={p.get('customization')} buyer_type={p.get('buyer_type')}")
        print(f"parser self-confidence: {p.get('confidence')}   latency: {parse_ms:.0f} ms")

    # ---- admin governance aggregates ----------------------------------------
    admin = login(c, "admin@karvantana.demo", "admin-demo-1234")
    r = c.get(f"{API}/admin/ai/monitoring", headers=admin)
    if r.status_code == 200:
        m = r.json()
        print()
        print("=== AI GOVERNANCE (all recorded runs) ===")
        print(f"total AI requests      : {m['requests']}")
        print(f"success rate           : {m['success_rate']}%")
        print(f"avg latency (all tasks): {m['avg_latency_ms']} ms")
        print(f"low-confidence outputs : {m['low_confidence_outputs']} (<0.75)")
        print(f"human corrections      : {m['human_corrections']}")
        print(f"est. cost (demo)       : ${m['estimated_cost_usd']}")
        for t in m["by_task"]:
            print(f"  · {t['task']:<20} {t['requests']:>4} requests   {t['avg_latency_ms']:>5} ms avg")


if __name__ == "__main__":
    main()
