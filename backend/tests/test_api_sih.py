"""SIH evidence API tests: RBAC, honesty invariants, CRUD, computed impact."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module", autouse=True)
def _sih_seed():
    """Seed SIH evidence content into the isolated test DB (idempotent)."""
    import seed_sih  # the seeder is idempotent and DB-agnostic
    seed_sih.seed()


def test_sih_requires_auth(client):
    assert client.get("/api/v1/sih/readiness").status_code == 401


def test_sih_readiness_forbidden_for_buyer(client, buyer):
    r = client.get("/api/v1/sih/readiness", headers=buyer["auth"])
    assert r.status_code == 403


def test_sih_readiness_rollup(client, admin):
    r = client.get("/api/v1/sih/readiness", headers=admin["auth"])
    assert r.status_code == 200
    data = r.json()
    criteria = {c["criterion"] for c in data["criteria"]}
    assert criteria == {"PROBLEM_FIT", "INNOVATION", "FEASIBILITY", "TECH_DEPTH", "PRESENTATION"}
    for c in data["criteria"]:
        assert c["total"] > 0
        assert c["completion_pct"] is not None
    assert 0 <= data["overall_pct"] <= 100
    # seeder content present
    all_items = [i for c in data["criteria"] for i in c["items"]]
    assert any(i["code"] == "pf-research" and i["status"] == "MISSING" for i in all_items)
    assert any(i["status"] == "DEMO_READY" for i in all_items)


def test_checklist_update_requires_admin(client, buyer):
    r = client.patch("/api/v1/sih/checklist/does-not-exist", json={"status": "COMPLETE"}, headers=buyer["auth"])
    assert r.status_code == 403


def test_checklist_update_roundtrip(client, admin):
    roll = client.get("/api/v1/sih/readiness", headers=admin["auth"]).json()
    item = next(i for c in roll["criteria"] for i in c["items"] if i["code"] == "pf-research")
    r = client.patch(f"/api/v1/sih/checklist/{item['id']}",
                     json={"status": "PARTIALLY_COMPLETE", "evidence": "test evidence"}, headers=admin["auth"])
    assert r.status_code == 200
    assert r.json()["status"] == "PARTIALLY_COMPLETE"
    # restore
    client.patch(f"/api/v1/sih/checklist/{item['id']}", json={"status": "MISSING", "evidence": item["evidence"]},
                 headers=admin["auth"])


def test_research_record_privacy_roundtrip(client, admin):
    r = client.post("/api/v1/sih/research", headers=admin["auth"], json={
        "research_type": "INTERVIEW", "respondent_id": "R-001", "respondent_type": "ARTISAN",
        "craft_category": "Handloom", "location_district": "Madurai", "location_state": "Tamil Nadu",
        "language": "ta", "consent_status": "ANONYMIZED",
        "pain_points": {"pricing": True, "photography": True},
        "key_finding": "Test finding"})
    assert r.status_code == 200
    rid = r.json()["id"]
    rows = client.get("/api/v1/sih/research", headers=admin["auth"]).json()
    row = next(x for x in rows if x["id"] == rid)
    assert row["location_state"] == "Tamil Nadu"
    assert row["validation_status"] == "COMPLETE"
    # no PII fields exist on the serializer at all
    assert "phone" not in row and "email" not in row and "name" not in row


def test_research_rejects_bad_type(client, admin):
    r = client.post("/api/v1/sih/research", headers=admin["auth"],
                    json={"research_type": "GOSSIP", "consent_status": "GRANTED"})
    assert r.status_code == 422


def test_competitor_matrix_honesty(client, admin):
    rows = client.get("/api/v1/sih/competitors", headers=admin["auth"]).json()
    assert len(rows) >= 60  # 5 competitors x 13 capabilities
    unevaluated = [r for r in rows if r["value"] == "NOT_EVALUATED"]
    assert len(unevaluated) >= 45  # honesty: most cells carry no claim
    karv = [r for r in rows if r["is_karvantana"]]
    offline = next(r for r in karv if r["capability"] == "offline_first")
    assert offline["value"] == "NO"  # we do not lie about offline
    sourced = next(r for r in rows if r["competitor"] == "IndiaHandmade" and r["capability"] == "marketplace_access")
    assert sourced["value"] == "YES" and sourced["source"] and sourced["verification_status"] == "COMPLETE"


def test_set_competitor_cell_requires_source_for_complete(client, admin):
    r = client.post("/api/v1/sih/competitors", headers=admin["auth"], json={
        "competitor": "Amazon Karigar", "capability": "artisan_focus", "value": "PARTIAL"})
    assert r.status_code == 200
    body = r.json()
    assert body["verification_status"] == "PENDING_VALIDATION"  # no source => stays pending
    r2 = client.post("/api/v1/sih/competitors", headers=admin["auth"], json={
        "competitor": "Amazon Karigar", "capability": "artisan_focus", "value": "PARTIAL",
        "source": "https://www.amazon.in/karigar (accessed today)"})
    assert r2.json()["verification_status"] == "COMPLETE"


def test_problem_links_roundtrip(client, admin):
    rows = client.get("/api/v1/sih/problem-links", headers=admin["auth"]).json()
    assert len(rows) >= 5
    assert all("validation_metric" in r for r in rows)
    seeded = [r for r in rows if r["observed"] is None]
    assert seeded, "pending validations must exist until real measurement"


def test_impact_computed_from_real_rows(client, admin):
    data = client.get("/api/v1/sih/impact/computed", headers=admin["auth"]).json()
    comp = data["computed"]
    assert "demo" in comp["dataset"].lower()  # dataset disclosed
    de = comp["digital_enablement"]
    # structural: real integers with sample sizes (test DB may be empty when this file runs alone)
    assert isinstance(de["artisans_onboarded"]["value"], int)
    assert isinstance(de["products_digitized"]["value"], int)
    ai = comp["ai_performance"]
    assert isinstance(ai["catalogue_generations"]["value"], int)
    # manual metric definitions seeded with no fabricated values
    defs = data["manual_definitions"]
    assert len(defs) >= 13
    assert all(m["actual"] is None for m in defs)  # no invented observations


def test_metric_observation_provenance(client, admin):
    r = client.post("/api/v1/sih/impact/ai-accept/observation", headers=admin["auth"],
                    json={"actual": 50.0, "provenance": "TARGET"})
    assert r.status_code == 200
    assert r.json()["provenance"] == "TARGET"
    data = client.get("/api/v1/sih/impact/computed", headers=admin["auth"]).json()
    row = next(m for m in data["manual_definitions"] if m["code"] == "ai-accept")
    assert row["validation_status"] == "TARGET"  # a target is never shown as REAL


def test_judge_questions_seeded_and_answerable(client, admin):
    rows = client.get("/api/v1/sih/judge-questions", headers=admin["auth"]).json()
    assert len(rows) >= 35
    sections = {r["section"] for r in rows}
    assert {"PROBLEM", "INNOVATION", "TECHNICAL", "FEASIBILITY", "BUSINESS", "IMPACT"} <= sections
    q = next(r for r in rows if r["section"] == "PROBLEM")
    r = client.patch(f"/api/v1/sih/judge-questions/{q['id']}",
                     json={"answer": "Updated truthful answer.", "validation_status": "COMPLETE"},
                     headers=admin["auth"])
    assert r.status_code == 200


def test_risks_register_complete(client, admin):
    rows = client.get("/api/v1/sih/risks", headers=admin["auth"]).json()
    ids = {r["risk_id"] for r in rows}
    assert len(rows) == 18
    assert f"R-{len(rows):02d}" in ids
    r4 = next(r for r in rows if r["risk_id"] == "R-04")
    assert r4["status"] == "MITIGATED_IN_BUILD" and r4["validation"]  # hallucination risk has a verifiable mitigation
    r2 = next(r for r in rows if r["risk_id"] == "R-02")
    assert "NOT yet shipped" in r2["validation"]  # honesty about offline


def test_tech_scouting_ai_pipelines(client, admin):
    rows = client.get("/api/v1/sih/tech-scouting", headers=admin["auth"]).json()
    ai_rows = [r for r in rows if r["ai_model"]]
    assert len(ai_rows) >= 5
    for r in ai_rows:
        assert r["ai_input"] and r["ai_output"] and r["ai_human_override"]
    planned = [r for r in rows if not r["in_current_build"]]
    assert any("Flutter" in r["technology"] for r in planned)


def test_prior_art_never_claims_absence(client, admin):
    rows = client.get("/api/v1/sih/prior-art", headers=admin["auth"]).json()
    assert len(rows) >= 2
    assert all("no patent exists" not in (r["notes"] or "") for r in rows)


def test_references_have_access_dates(client, admin):
    rows = client.get("/api/v1/sih/references", headers=admin["auth"]).json()
    assert len(rows) >= 4
    assert all(r["accessed_date"] for r in rows)
    assert any(r["organization"] and "Ministry of Textiles" in r["organization"] for r in rows)


def test_evidence_pack_export(client, admin):
    r = client.get("/api/v1/sih/evidence-pack/export", headers=admin["auth"])
    assert r.status_code == 200
    assert "SIH Evidence Pack" in r.text
    assert "Risk Register" in r.text
    assert "PENDING VALIDATION" in r.text or "PENDING_VALIDATION" in r.text


def test_test_report_reads_real_artifact(client, admin):
    data = client.get("/api/v1/sih/tests", headers=admin["auth"]).json()
    # The artifact is regenerated by whichever pytest run wrote it last; the test
    # DB's own run happens at the END of this session, so only structure is asserted here.
    if data["available"]:
        assert data["total"] >= 1
        assert data["passed"] + data["failed"] + data["skipped"] == data["total"]
        assert "test-results.xml" in data["source"]
    else:
        # permitted only when no artifact exists yet — the note explains how to make one
        assert "junitxml" in data["note"] or "Run" in data["note"]


def test_approval_recording_and_impact_linkage(client, artisan, admin):
    # create a product this artisan owns (self-sufficient: does not rely on other test files)
    created = client.post("/api/v1/products", headers=artisan["auth"],
                          json={"title": "Audit Trail Test Piece", "category": "textiles"})
    assert created.status_code == 200, created.text
    pid = created.json()["id"]
    before = client.get("/api/v1/sih/impact/computed", headers=admin["auth"]).json()
    before_accept = before["computed"]["ai_performance"]["ai_acceptance"]["value"]
    r = client.post("/api/v1/sih/approvals", headers=artisan["auth"], json={
        "product_id": pid, "field": "title",
        "original_output": {"value": "AI Title"}, "final_output": {"value": "AI Title"},
        "action": "APPROVE", "confidence": 0.86})
    assert r.status_code == 200
    # admin sees acceptance reflected in computed impact
    after = client.get("/api/v1/sih/impact/computed", headers=admin["auth"]).json()
    after_accept = after["computed"]["ai_performance"]["ai_acceptance"]["value"]
    assert after_accept == before_accept + 1  # the approval we just recorded
