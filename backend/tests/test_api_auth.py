"""API tests: authentication + RBAC."""

from __future__ import annotations


def test_register_login_me_flow(client):
    r = client.post("/api/v1/auth/register", json={"full_name": "Flow User", "email": "flow@tests.io", "password": "password1", "role": "BUYER"})
    assert r.status_code == 200
    tokens = r.json()
    assert tokens["access_token"] and tokens["refresh_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200 and me.json()["role"] == "BUYER"
    login = client.post("/api/v1/auth/login", json={"email": "flow@tests.io", "password": "password1"})
    assert login.status_code == 200


def test_duplicate_email_conflict(client):
    r = client.post("/api/v1/auth/register", json={"full_name": "Dup", "email": "flow@tests.io", "password": "password1", "role": "BUYER"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CONFLICT"


def test_wrong_password_uniform_error(client):
    r = client.post("/api/v1/auth/login", json={"email": "flow@tests.io", "password": "wrong-pass-9"})
    assert r.status_code == 401


def test_refresh_rotation(client):
    tokens = client.post("/api/v1/auth/register", json={"full_name": "Rot User", "email": "rot@tests.io", "password": "password1", "role": "BUYER"}).json()
    r1 = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r1.status_code == 200
    # replaying the old token must fail (rotation)
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r2.status_code == 401


def test_otp_login_creates_account(client):
    otp = client.post("/api/v1/auth/otp/request", json={"phone": "+91 91234 56780"}).json()
    assert otp["demo_code"], "demo env returns the code for testing"
    r = client.post("/api/v1/auth/otp/verify", json={"phone": "+91 91234 56780", "code": otp["demo_code"], "full_name": "OTP User"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "ARTISAN"


def test_rbac_blocks_buyer_from_product_creation(client, buyer):
    response = client.post("/api/v1/products", headers=buyer["auth"], json={"title": "x"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_rbac_blocks_artisan_from_admin(client, artisan):
    r = client.get("/api/v1/analytics/admin/overview", headers=artisan["auth"])
    assert r.status_code == 403


def test_unauthenticated_marketplace_is_public(client):
    r = client.get("/api/v1/products")
    assert r.status_code == 200
