from app.main import create_app
from fastapi.testclient import TestClient


def test_replay_bootstrap_and_contract():
    with TestClient(create_app()) as c:
        matches = c.get("/api/v1/matches?league=worlds&status=live").json()
        assert matches[0]["matchId"] == "demo-worlds"
        match = matches[0]["matchId"]
        snapshot = c.get(f"/api/v1/matches/{match}/sync").json()
        assert snapshot["sourceMode"] == "replay"
        assert snapshot["state"]["blue"]["shortName"] == "T1"
        assert snapshot["streamCursor"].count(":") == 1
        assert c.get("/api/v1/matches/missing/state").status_code == 404
        assert c.get(f"/api/v1/matches/{match}/events?limit=101").status_code == 422
        assert c.get("/api/v1/health").json()["sourceStatus"] == "replay"


def test_live_mode_without_explicit_approval_fails_closed(monkeypatch):
    monkeypatch.setenv("SOURCE_MODE", "live")
    monkeypatch.delenv("SOURCE_APPROVED", raising=False)
    monkeypatch.delenv("LOLESPORTS_API_KEY", raising=False)
    with TestClient(create_app()) as c:
        assert c.get("/api/v1/matches").json() == []
        assert c.get("/api/v1/health").json()["sourceStatus"] == "access_denied"
