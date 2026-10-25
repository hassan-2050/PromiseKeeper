from fastapi.testclient import TestClient
from app import main

client = TestClient(main.app)

def test_import_checks_evidence_and_rejects_unsupported_quote(monkeypatch):
    async def fake_extract(text, timestamp):
        return [
            {"claim": "send the report", "owner": "Maya", "recipient": "Alex", "deadline": "Friday", "conditionality": None, "certainty": "suggested", "evidence": "I'll send the report by Friday.", "action": "Wait for the report"},
                {"claim": "send the report", "owner": "Maya", "recipient": "Alex", "deadline": "Friday", "conditionality": None, "certainty": "suggested", "evidence": "I'll send the report by Friday!", "action": "Wait for the report"},
            {"claim": "invented", "owner": "Nobody", "recipient": None, "deadline": None, "conditionality": None, "certainty": "suggested", "evidence": "not in source", "action": "Do it"},
                {"claim": "send the summary", "owner": "Omar", "recipient": None, "deadline": None, "conditionality": None, "certainty": "suggested", "evidence": "I will not send the summary.", "action": "Wait"},
        ]
    monkeypatch.setattr(main, "extract_local", fake_extract)
    response = client.post("/api/import", json={"name":"test notes", "text":"Maya: I'll send the report by Friday.\nMaya: I'll send the report by Friday!\nOmar: I will not send the summary."})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["commitments"][0]["evidence"] == "I'll send the report by Friday."
    assert data["commitments"][0]["fragment_id"]
    assert data["commitments"][0]["location"]["start"] == 0
    assert len(data["commitments"][0]["evidence_quotes"]) == 2
    dismissed = client.patch(f"/api/commitments/{data['commitments'][0]['id']}", json={"status":"rejected"})
    assert dismissed.json()["status"] == "rejected"
    client.delete(f"/api/sources/{data['source_id']}")

def test_clear_non_commitments_are_filtered_but_conditional_intent_is_kept():
    assert main.non_commitment_quote("I will not send the report.")
    assert main.non_commitment_quote("I already sent the report.")
    assert main.non_commitment_quote("I could send the slides if you need them.")
    assert not main.non_commitment_quote("If the lab clears the samples, I'll upload the appendix.")

def test_relative_deadline_requires_source_timestamp():
    from datetime import datetime
    assert main.resolve_deadline_text("tomorrow", None) is None
    assert main.resolve_deadline_text("Friday", None) is None
    assert main.resolve_deadline_text("tomorrow", datetime.fromisoformat("2026-10-24T09:00:00")) == "2026-10-25"
    assert main.resolve_deadline_text("2026-11-03", None) == "2026-11-03"

def test_followup_requires_approval(monkeypatch):
    async def fake_extract(text, timestamp):
        return [{"claim":"share the figures", "owner":"Jon", "recipient":None, "deadline":None, "conditionality":None, "certainty":"suggested", "evidence":"I will share the figures.", "action":"Check in"}]
    monkeypatch.setattr(main, "extract_local", fake_extract)
    data=client.post("/api/import",json={"text":"I will share the figures."}).json()
    item=data["commitments"][0]
    assert client.post(f"/api/commitments/{item['id']}/draft",json={}).status_code==409
    client.patch(f"/api/commitments/{item['id']}",json={"status":"confirmed", "note":"Ask after the lab meeting"})
    assert client.get("/api/commitments").json()[0]["notes"] == "Ask after the lab meeting"
    with main.Session() as db:
        assert db.query(main.AuditEvent).filter_by(commitment_id=item["id"]).count() == 1
    draft=client.post(f"/api/commitments/{item['id']}/draft",json={})
    assert draft.status_code==200
    assert draft.json()["requires_human_review"] is True
    assert draft.json()["sent"] is False
    assert "check in about the figures" in draft.json()["text"]
    assert "follow up on share" not in draft.json()["text"]
    assert client.patch(f"/api/commitments/{item['id']}",json={"status":"complete"}).json()["status"] == "complete"
    client.delete(f"/api/sources/{data['source_id']}")
    with main.Session() as db:
        assert db.query(main.Draft).filter_by(commitment_id=item["id"]).count() == 0


def test_remote_flag_requires_per_import_consent_and_preserves_quote_and_approval_boundaries(monkeypatch):
    from app import tinker_runtime
    monkeypatch.setattr(main, "EXTRACTION_PROVIDER", "tinker")
    calls = []
    async def fake_remote(text, timestamp):
        calls.append(text)
        return [
            {"claim": "send the vendor packet", "owner": "Amina", "evidence": "I'll send the vendor packet.", "action": "Review"},
            {"claim": "invented", "owner": "Nobody", "evidence": "fabricated quote", "action": "Review"},
            {"claim": "send the report", "owner": "Bilal", "evidence": "I will not send the report.", "action": "Review"},
        ]
    monkeypatch.setattr(tinker_runtime, "extract_tinker", fake_remote)
    body = {"name": "Synthetic remote regression", "text": "Amina: I'll send the vendor packet.\nBilal: I will not send the report."}
    assert client.post("/api/import", json=body).status_code == 422
    assert calls == []
    response = client.post("/api/import", json={**body, "allow_remote_inference": True})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    item = data["commitments"][0]
    assert item["status"] == "suggested"
    assert client.post(f"/api/commitments/{item['id']}/draft", json={}).status_code == 409
    assert client.patch(f"/api/commitments/{item['id']}", json={"status": "confirmed"}).status_code == 200
    assert client.post(f"/api/commitments/{item['id']}/draft", json={}).json()["requires_human_review"]
    assert client.delete(f"/api/sources/{data['source_id']}").status_code == 200
    assert not any(c["source_id"] == data["source_id"] for c in client.get("/api/commitments").json())
