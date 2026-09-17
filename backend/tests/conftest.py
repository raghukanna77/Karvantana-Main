"""Pytest fixtures: isolated temp DB per session + API client helpers."""

from __future__ import annotations

import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix="karvantana_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["MEDIA_DIR"] = os.path.join(_tmp, "media")
os.environ["JWT_SECRET"] = "test-secret-not-for-production"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app import models  # noqa: F401,E402  register all models


@pytest.fixture(scope="session", autouse=True)
def _db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def _register(client: TestClient, email: str, password: str, role: str, name: str) -> dict:
    r = client.post("/api/v1/auth/register", json={"full_name": name, "email": email, "password": password, "role": role})
    assert r.status_code == 200, r.text
    return r.json()


def _login(client: TestClient, email: str, password: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="session")
def artisan(client):
    tokens = _register(client, "artisan@tests.io", "artisan-pass-1", "ARTISAN", "Test Artisan")
    auth = {"Authorization": f"Bearer {tokens['access_token']}"}
    # complete onboarding (creates the artisan profile progressively)
    r = client.post("/api/v1/artisans/me/onboarding", headers=auth, json={
        "step": 3,
        "data": {"display_name": "Test Artisan Studio", "craft_specialization": "Handloom Weaving",
                 "state": "Tamil Nadu", "district": "Madurai", "years_of_experience": 8,
                 "organization_type": "INDIVIDUAL"}})
    assert r.status_code == 200, r.text
    assert r.json()["onboarding_complete"] is True
    return {"auth": auth, "user": tokens["user"]}


@pytest.fixture(scope="session")
def buyer(client):
    tokens = _register(client, "buyer@tests.io", "buyer-pass-1", "BUYER", "Test Buyer")
    return {"auth": {"Authorization": f"Bearer {tokens['access_token']}"}, "user": tokens["user"]}


@pytest.fixture(scope="session")
def admin(client, db_session):
    from app.models.user import User

    db = SessionLocal()
    tokens = _register(client, "admin@tests.io", "admin-pass-1", "BUYER", "Temp Admin")
    user = db.query(User).filter(User.email == "admin@tests.io").first()
    user.role = "ADMIN"  # admin accounts are provisioned internally, not self-serve
    db.commit()
    db.close()
    return {"auth": {"Authorization": f"Bearer {tokens['access_token']}"}, "user": tokens["user"]}


@pytest.fixture(scope="session")
def db_session():
    return SessionLocal()
