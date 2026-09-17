"""Integration test: the critical KARVANTANA journey, end to end.

Artisan → Product Capture → Voice → AI Catalogue → Pricing → Publish →
Buyer → Order → Payment → Delivery → Review → Reputation → Repeat Order
plus the B2B bulk path. Mirrors the non-negotiable product journey.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw

TAMIL_SAREE = "இது கைத்தறியில் நெய்த பருத்தி சேலை. இயற்கை நிறம் பயன்படுத்தியிருக்கோம். இதை நாலு நாள்ல தயாரிக்க முடியும்."


def _jpeg() -> bytes:
    img = Image.new("RGB", (640, 640), (150, 90, 70))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((160, 160, 480, 480), radius=32, fill=(120, 60, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def published_product(client, artisan):
    # voice → extraction
    voice = client.post("/api/v1/ai/voice/transcribe", headers=artisan["auth"], json={"text": TAMIL_SAREE}).json()
    assert voice["language"] == "ta"
    assert voice["extracted"]["material"]["value"] == "cotton"
    # draft + photo
    pid = client.post("/api/v1/products", headers=artisan["auth"], json={"title": "", "category": "Sarees"}).json()["id"]
    up = client.post(f"/api/v1/products/{pid}/images", headers=artisan["auth"], files={"file": ("p.jpg", _jpeg(), "image/jpeg")})
    assert up.status_code == 200 and up.json()["quality_score"] is not None
    # catalogue
    cat = client.post("/api/v1/ai/catalogue/generate", headers=artisan["auth"],
                      json={"product_id": pid, "transcript_en": voice["translated"], "transcript_original": voice["transcript"]}).json()
    assert cat["title"]
    assert cat["confidence"] > 0.5
    # artisan edits + pricing sanity
    rec = client.post("/api/v1/ai/pricing/recommend", headers=artisan["auth"],
                      json={"material_cost": 420, "labour_cost": 380, "packaging_cost": 40, "shipping_estimate": 60,
                            "category_hint": "saree", "product_id": pid}).json()
    assert rec["suggested_price"] >= 850
    price = rec["suggested_price"]
    r = client.patch(f"/api/v1/products/{pid}", headers=artisan["auth"],
                     json={"title": cat["title"], "short_description": cat["short_description"], "description": cat["description"],
                           "material": "Cotton", "technique": "Handloom", "production_days": 4, "price": price,
                           "inventory_mode": "MADE_TO_ORDER", "keywords": cat["keywords"]})
    assert r.status_code == 200
    pub = client.post(f"/api/v1/products/{pid}/publish", headers=artisan["auth"])
    assert pub.status_code == 200 and pub.json()["lifecycle"] == "PUBLISHED"
    return {"id": pid, "price": price}


def test_publish_requires_photo(client, artisan):
    voice = client.post("/api/v1/ai/voice/transcribe", headers=artisan["auth"], json={"text": TAMIL_SAREE}).json()
    pid = client.post("/api/v1/products", headers=artisan["auth"], json={"title": "No photo item"}).json()["id"]
    client.patch(f"/api/v1/products/{pid}", headers=artisan["auth"], json={"price": 100})
    r = client.post(f"/api/v1/products/{pid}/publish", headers=artisan["auth"])
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "PUBLISH_INCOMPLETE"


def test_buyer_search_finds_published_product(client, published_product):
    r = client.get("/api/v1/products", params={"q": "handwoven saree under 1500"})
    assert r.status_code == 200
    assert r.json()["interpreted"]["max_price"] == 1500
    assert any(p["id"] == published_product["id"] for p in r.json()["items"])


def test_full_order_flow_with_idempotency_and_review(client, buyer, artisan, published_product):
    headers = {**buyer["auth"], "Idempotency-Key": "test-order-1"}
    r = client.post("/api/v1/orders", headers=headers, json={
        "items": [{"product_id": published_product["id"], "quantity": 1}],
        "shipping_address": {"line1": "1 Test Lane", "city": "Mysuru", "pincode": "570001"}})
    assert r.status_code == 200
    order = r.json()
    # idempotent replay returns the same order
    replay = client.post("/api/v1/orders", headers=headers, json={
        "items": [{"product_id": published_product["id"], "quantity": 1}], "shipping_address": {}})
    assert replay.json()["id"] == order["id"]

    # payment: server-verified only
    intent = client.post("/api/v1/payments/create-intent", headers=buyer["auth"], json={"order_id": order["id"]}).json()
    assert intent["provider"] == "demo" and intent["demo"] is True
    settle = client.post("/api/v1/payments/demo/confirm", headers=buyer["auth"], json={"provider_payment_id": intent["provider_payment_id"]})
    assert settle.json().get("order_status") == "CONFIRMED"
    # replayed webhook event is acknowledged, not re-applied
    again = client.post("/api/v1/payments/demo/confirm", headers=buyer["auth"], json={"provider_payment_id": intent["provider_payment_id"]})
    assert again.status_code == 200

    # illegal transition guard: buyer cannot jump to SHIPPED
    bad = client.post(f"/api/v1/orders/{order['id']}/status", headers=buyer["auth"], json={"status": "SHIPPED"})
    assert bad.status_code == 409

    # artisan fulfils
    for st in ("IN_PRODUCTION", "READY_TO_SHIP", "SHIPPED", "DELIVERED", "COMPLETED"):
        r = client.post(f"/api/v1/orders/{order['id']}/status", headers=artisan["auth"], json={"status": st})
    assert r.json()["status_label"] == "Completed"

    # verified review gating: cannot review before completion is impossible here,
    # but a second review on the same item is blocked
    detail = client.get(f"/api/v1/orders/{order['id']}", headers=buyer["auth"]).json()
    item_id = detail["items"][0]["id"]
    r1 = client.post(f"/api/v1/products/{published_product['id']}/reviews", headers=buyer["auth"],
                     json={"order_item_id": item_id, "product_rating": 5, "text": "Lovely."})
    assert r1.status_code == 200
    r2 = client.post(f"/api/v1/products/{published_product['id']}/reviews", headers=buyer["auth"],
                     json={"order_item_id": item_id, "product_rating": 4})
    assert r2.status_code == 409

    # relationship commerce: follow + direct reorder
    art_id = client.get(f"/api/v1/products/{published_product['id']}", headers=buyer["auth"]).json()["artisan"]["id"]
    assert client.post(f"/api/v1/artisans/{art_id}/follow", headers=buyer["auth"]).status_code == 200
    reorder = client.post(f"/api/v1/orders/{order['id']}/reorder", headers=buyer["auth"])
    assert reorder.status_code == 200 and reorder.json()["order_number"]


def _publish_product(client, artisan, title: str, price: float, category: str = "Storage") -> str:
    pid = client.post("/api/v1/products", headers=artisan["auth"], json={"title": title, "category": category}).json()["id"]
    client.post(f"/api/v1/products/{pid}/images", headers=artisan["auth"], files={"file": ("p.jpg", _jpeg(), "image/jpeg")})
    client.patch(f"/api/v1/products/{pid}", headers=artisan["auth"], json={"price": price, "inventory_mode": "STOCK", "stock_quantity": 50, "keywords": f"{title.lower()}, handmade"})
    r = client.post(f"/api/v1/products/{pid}/publish", headers=artisan["auth"])
    assert r.status_code == 200, r.text
    return pid


def test_b2b_bulk_requirement_to_order(client, buyer, artisan):
    # a cheap in-stock product the requirement can match against
    _publish_product(client, artisan, "Handmade Test Basket", 450)
    r = client.post("/api/v1/bulk-requests", headers=buyer["auth"], json={
        "title": "Event gift baskets", "description": "100 handmade bamboo baskets for a corporate event",
        "quantity": 100, "max_unit_price": 500, "customization_required": True})
    assert r.status_code == 200
    parsed = r.json()["parsed"]
    assert parsed["quantity"] == 100 and parsed["buyer_type"] == "CORPORATE"
    req_id = r.json()["id"]
    matches = client.get(f"/api/v1/bulk-requests/{req_id}/matches", headers=buyer["auth"]).json()["matches"]
    assert matches and matches[0]["reasons"]
    mine = client.get("/api/v1/bulk-requests/mine", headers=buyer["auth"])
    assert mine.status_code == 200


def test_assistant_only_answers_from_tools(client, artisan):
    r = client.post("/api/v1/ai/assistant/ask", headers=artisan["auth"], json={"question": "Show me my pending orders."})
    assert r.status_code == 200
    body = r.json()
    assert body["tool"] == "pending_orders"
    assert "sources" in body


def test_admin_overview_and_ai_monitoring(client, admin):
    overview = client.get("/api/v1/analytics/admin/overview", headers=admin["auth"])
    assert overview.status_code == 200 and "gmv" in overview.json()
    ai = client.get("/api/v1/admin/ai/monitoring", headers=admin["auth"])
    assert ai.status_code == 200 and ai.json()["requests"] >= 0


def test_catalogue_export_canonical(client, artisan):
    r = client.get("/api/v1/export/catalogue", headers=artisan["auth"])
    assert r.status_code == 200
    body = r.json()
    assert body["format"] == "karvantana.catalogue.v1"
    assert "adapter_note" in body and "DEMO" in body["adapter_note"]
    for p in body["products"]:
        assert {"product_id", "title", "pricing", "artisan", "media"} <= set(p.keys())
