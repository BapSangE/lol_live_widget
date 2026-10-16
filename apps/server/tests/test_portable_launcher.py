import json
import sys
from pathlib import Path

import httpx
import pytest


def test_embedded_server_owns_dynamic_loopback_port_and_stops(monkeypatch):
    from scripts.portable_launcher import EmbeddedServer

    monkeypatch.setenv("SOURCE_MODE", "live")
    monkeypatch.setenv("SOURCE_APPROVED", "false")
    with EmbeddedServer(demo=True) as server:
        origin = server.origin
        assert origin.startswith("http://127.0.0.1:")
        response = httpx.get(origin + "/api/v1/health", timeout=5)
        assert response.json()["sourceMode"] == "replay"
        assert (
            httpx.get(origin + "/api/v1/matches").json()[0]["matchId"] == "demo-worlds"
        )
    assert not server.thread.is_alive()
    assert server.socket.fileno() == -1
    # Windows may silently drop a connection to a closed port instead of
    # immediately refusing it; both confirm the stopped server is unreachable.
    with pytest.raises((httpx.ConnectError, httpx.ConnectTimeout)):
        httpx.get(origin + "/api/v1/health", timeout=0.2)


def test_frozen_replay_uses_bundled_fixture_root(monkeypatch, tmp_path):
    from app.providers.replay import ReplayProvider

    original = Path(__file__).resolve().parents[3] / "fixtures/raw_frames/demo.json"
    target = tmp_path / "fixtures/raw_frames/demo.json"
    target.parent.mkdir(parents=True)
    frames = json.loads(original.read_text())
    frames[0]["matchId"] = "bundled-fixture"
    target.write_text(json.dumps(frames))
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.delenv("REPLAY_FIXTURE", raising=False)
    assert ReplayProvider().frames[0].match_id == "bundled-fixture"


def test_macos_server_mode_publishes_origin_and_stops_cleanly(tmp_path):
    import threading

    from scripts.portable_launcher import serve_embedded_server

    port_file = tmp_path / "collector.port"
    stop = threading.Event()
    thread = threading.Thread(
        target=serve_embedded_server, args=(port_file, stop), daemon=True
    )
    thread.start()
    try:
        for _ in range(100):
            if port_file.exists():
                break
            threading.Event().wait(0.05)
        origin = port_file.read_text()
        assert origin.startswith("http://127.0.0.1:")
        assert (
            httpx.get(origin + "/api/v1/health", timeout=5).json()["sourceMode"]
            == "live"
        )
    finally:
        stop.set()
        thread.join(timeout=5)
    assert not thread.is_alive()
