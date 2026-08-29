from fastapi.testclient import TestClient

from nightdesk.api import app
from nightdesk.seed import seed_hold_receipts


def test_unauthenticated_post_rejected_when_token_unset(monkeypatch) -> None:
    monkeypatch.delenv("SHIFT_TOKEN", raising=False)
    with TestClient(app) as client:
        shift = client.post("/api/shifts", json={"goal": "stamp", "force_mock": True})
        assert shift.status_code == 403
        reset = client.post("/api/reset")
        assert reset.status_code == 403


def test_unauthenticated_post_rejected_when_token_required(monkeypatch) -> None:
    monkeypatch.setenv("SHIFT_TOKEN", "correct-horse")
    with TestClient(app) as client:
        bare = client.post("/api/shifts", json={"goal": "stamp", "force_mock": True})
        assert bare.status_code == 403
        wrong = client.post(
            "/api/shifts",
            json={"goal": "stamp", "force_mock": True},
            headers={"X-Shift-Token": "nope"},
        )
        assert wrong.status_code == 403
        reset = client.post("/api/reset")
        assert reset.status_code == 403


def test_seeded_get_shows_hold_receipts() -> None:
    seed_hold_receipts()
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        body = client.get("/api/cases")
        assert body.status_code == 200
        cases = body.json()["cases"]
        assert len(cases) >= 10
        assert {c["id"] for c in cases} >= {"CASE-2404", "CASE-2409"}
        for case in cases:
            note = case["note"]
            assert note is not None
            assert note["why_human"]
            assert isinstance(note["present"], list)
            assert isinstance(note["missing"], list)
            assert note["missing"] or note["present"]
            assert case["final_disposition"] == "HOLD"
            assert note["recommended"] == "HOLD"
            assert "AUTO_CLOSE" not in note["summary"]
