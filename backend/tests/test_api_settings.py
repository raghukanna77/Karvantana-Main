"""PATCH /auth/me settings tests: language, easy mode, font scale, validation."""

from __future__ import annotations


def test_settings_language_roundtrip(client, artisan):
    auth = artisan["auth"]
    res = client.patch("/api/v1/auth/me", json={"preferred_language": "ta"}, headers=auth)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["preferred_language"] == "ta"
    assert body["settings"]["preferred_language"] == "ta"
    res = client.get("/api/v1/auth/me", headers=auth)
    assert res.json()["preferred_language"] == "ta"
    # restore
    client.patch("/api/v1/auth/me", json={"preferred_language": "en"}, headers=auth)


def test_settings_easy_mode_and_font(client, artisan):
    auth = artisan["auth"]
    res = client.patch("/api/v1/auth/me", json={"easy_mode_enabled": True, "font_scale": 1.25},
                       headers=auth)
    assert res.status_code == 200, res.text
    body = res.json()["settings"]
    assert body["easy_mode_enabled"] is True
    assert body["font_scale"] == 1.25


def test_settings_rejects_unknown_language(client, artisan):
    res = client.patch("/api/v1/auth/me", json={"preferred_language": "xx"}, headers=artisan["auth"])
    assert res.status_code == 422


def test_settings_rejects_font_scale_out_of_range(client, artisan):
    res = client.patch("/api/v1/auth/me", json={"font_scale": 3.0}, headers=artisan["auth"])
    assert res.status_code == 422


def test_settings_regional_pack_language_accepted(client, artisan):
    """Regional packs (gar = Garhwali) are first-class values, not second-class strings."""
    res = client.patch("/api/v1/auth/me", json={"preferred_language": "gar"}, headers=artisan["auth"])
    assert res.status_code == 200, res.text
    assert res.json()["preferred_language"] == "gar"
    client.patch("/api/v1/auth/me", json={"preferred_language": "en"}, headers=artisan["auth"])
