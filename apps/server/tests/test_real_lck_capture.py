"""Offline regression tests against captured, unmodified 2026 LCK responses.

This verifies one contiguous ~70-second sample, not the full game or live access.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest
from app.events.detector import Detector
from app.models.contracts import MatchSummary, RawFrame
from app.providers.lolesports import LoLEsportsProvider
from app.storage.memory import MemoryStore
from fastapi.testclient import TestClient

CAPTURE = (
    Path(__file__).resolve().parents[3]
    / "fixtures/captures/lck-2026-09-13-gen-hle-game1"
)
MATCH_ID = "117030752644841643"
GAME_ID = "117030752644841644"


def load_frames():
    return [
        RawFrame.model_validate(f)
        for f in json.loads((CAPTURE / "frames.json").read_text())
    ]


def test_captured_responses_have_recorded_integrity_and_correct_year():
    manifest = json.loads((CAPTURE / "manifest.json").read_text())
    assert manifest["matchDate"] == "2026-09-13"
    assert manifest["gameId"] == GAME_ID
    assert manifest["frameCount"] == 363
    assert manifest["credentialsUsed"] is False
    for request in manifest["requests"]:
        assert (
            hashlib.sha256((CAPTURE / request["file"]).read_bytes()).hexdigest()
            == request["sha256"]
        )
        assert request["httpStatus"] == 200


def test_normalizer_matches_real_source_stats_and_never_invents_game_clock():
    frames = load_frames()
    raw_start = json.loads((CAPTURE / "window-05-45-00.json").read_text())["frames"][0]
    raw_end = json.loads((CAPTURE / "window-05-46-00.json").read_text())["frames"][-1]
    for raw, normalized in [(raw_start, frames[0]), (raw_end, frames[-1])]:
        for side, team in [("blueTeam", normalized.blue), ("redTeam", normalized.red)]:
            result = LoLEsportsProvider._stats(raw[side], team)
            assert (result.kills, result.gold, result.towers) == (
                raw[side]["totalKills"],
                raw[side]["totalGold"],
                raw[side]["towers"],
            )
    assert (frames[0].blue.kills, frames[0].red.kills) == (3, 3)
    assert (frames[-1].blue.kills, frames[-1].red.kills) == (4, 4)
    assert (frames[-1].blue.gold, frames[-1].red.gold) == (27578, 28554)
    assert all(f.game_time_seconds is None and f.league == "lck" for f in frames)
    assert all(f.blue.series_wins == 0 and f.red.series_wins == 0 for f in frames)


def test_real_kill_changes_produce_two_team_events_and_one_fact_only_window():
    detector = Detector()
    events = [
        e
        for revision, frame in enumerate(load_frames(), 1)
        for e in detector.process(frame, revision)
    ]
    assert [(e.type, e.team_id) for e in events] == [
        ("KILL_DELTA", "100205573496804586"),
        ("KILL_DELTA", "100205573495116443"),
        ("MULTIKILL_WINDOW", None),
    ]
    assert events[0].message_ko == "HLE 킬 기록"
    assert events[1].message_ko == "GEN 킬 기록"
    assert events[2].message_ko == "관측 구간 GEN 1킬·HLE 1킬 기록"
    assert all(e.confidence == "derived" and e.occurred_at is None for e in events)
    assert all(
        "한타" not in e.message_ko and "솔로킬" not in e.message_ko for e in events
    )


def test_actual_player_kills_agree_between_window_and_details():
    window = json.loads((CAPTURE / "window-05-45-20.json").read_text())
    details = json.loads((CAPTURE / "details-kills.json").read_text())
    metadata = {
        p["participantId"]: p
        for side in ("blueTeamMetadata", "redTeamMetadata")
        for p in window["gameMetadata"][side]["participantMetadata"]
    }
    observed = []
    previous = None
    for raw in window["frames"]:
        current = {
            p["participantId"]: p
            for side in ("blueTeam", "redTeam")
            for p in raw[side]["participants"]
        }
        if previous:
            for player_id, stats in current.items():
                if stats["kills"] > previous[player_id]["kills"]:
                    observed.append(
                        (
                            metadata[player_id]["summonerName"],
                            metadata[player_id]["championId"],
                            stats["kills"],
                            stats["deaths"],
                            stats["assists"],
                        )
                    )
        previous = current
    assert observed == [
        ("HLE Kanavi", "Naafiri", 2, 1, 2),
        ("GEN Duro", "Milio", 1, 1, 3),
    ]
    detailed_by_time = {f["rfc460Timestamp"]: f for f in details["frames"]}
    checked = 0
    for raw in window["frames"]:
        detailed = detailed_by_time.get(raw["rfc460Timestamp"])
        if detailed is None:
            continue
        expected = {
            p["participantId"]: (p["kills"], p["deaths"], p["assists"])
            for side in ("blueTeam", "redTeam")
            for p in raw[side]["participants"]
        }
        assert {
            p["participantId"]: (p["kills"], p["deaths"], p["assists"])
            for p in detailed["participants"]
        } == expected
        checked += 1
    assert checked > 0


@pytest.mark.asyncio
async def test_real_frames_are_idempotent_in_store_and_stream_resume():
    frames = load_frames()
    store = MemoryStore("replay")
    await store.ingest(frames[0])
    initial = await store.sync(MATCH_ID)
    for frame in frames:
        await store.ingest(frame)
    complete = await store.sync(MATCH_ID)
    messages = await store.after(MATCH_ID, initial.stream_cursor)
    assert complete.state.revision == 333
    assert len(complete.events) == 3
    assert len([m for m in messages if m.event == "match_event"]) == 3
    assert await store.after(MATCH_ID, messages[-1].id) == []
    for frame in frames:
        await store.ingest(frame)
    repeated = await store.sync(MATCH_ID)
    assert repeated.stream_cursor == complete.stream_cursor
    assert [e.id for e in repeated.events] == [e.id for e in complete.events]


@pytest.mark.asyncio
async def test_terminal_capture_does_not_guess_a_winner():
    raw = json.loads((CAPTURE / "end.json").read_text())["frames"][-1]
    assert raw["gameState"] == "finished"
    assert (raw["blueTeam"]["totalKills"], raw["redTeam"]["totalKills"]) == (13, 13)
    base = load_frames()[0]
    end = base.model_copy(
        update={
            "source_timestamp": datetime.fromisoformat(raw["rfc460Timestamp"]),
            "status": "ended",
            "blue": LoLEsportsProvider._stats(raw["blueTeam"], base.blue),
            "red": LoLEsportsProvider._stats(raw["redTeam"], base.red),
        }
    )
    store = MemoryStore("replay")
    await store.ingest(end)
    snapshot = await store.sync(MATCH_ID)
    assert snapshot.state.status == "ended"
    assert snapshot.events == []
    assert snapshot.state.game_time_seconds is None


class CapturedProvider:
    """Controlled test transport containing real values and real source timestamps."""

    def __init__(self):
        self.frames = load_frames()
        self.index = 0

    async def list_matches(self):
        f = self.frames[self.index]
        return [
            MatchSummary(
                match_id=MATCH_ID,
                league="lck",
                blue=f.blue,
                red=f.red,
                game_id=GAME_ID,
                game_number=1,
            )
        ]

    async def get_match(self, match_id):
        assert match_id == MATCH_ID
        return (await self.list_matches())[0]

    async def get_game_frames(self, game_id, after_source_timestamp):
        assert game_id == GAME_ID
        return [
            f
            for f in self.frames[: self.index + 1]
            if after_source_timestamp is None
            or f.source_timestamp >= after_source_timestamp
        ]

    async def health(self):
        return {"availability": "replay", "latencyMs": 0, "errors": 0}

    async def close(self):
        pass


def test_actual_capture_through_collector_rest_and_sse_recovery(monkeypatch):
    from app import main

    source = CapturedProvider()
    monkeypatch.setenv("SOURCE_MODE", "replay")
    monkeypatch.setattr(main, "ReplayProvider", lambda *_args: source)
    with TestClient(main.create_app()) as client:
        listed = client.get("/api/v1/matches?league=lck&status=live").json()
        assert listed[0]["matchId"] == MATCH_ID
        before = client.get(f"/api/v1/matches/{MATCH_ID}/sync").json()
        assert before["state"]["blue"]["kills"] == 3
        assert before["events"] == []
        source.index = len(source.frames) - 1
        client.portal.call(
            client.app.state.poller.collect, client.app.state.poller.matches[0]
        )
        after = client.get(f"/api/v1/matches/{MATCH_ID}/sync").json()
        assert (after["state"]["blue"]["kills"], after["state"]["red"]["kills"]) == (
            4,
            4,
        )
        assert after["sourceMode"] == "replay"
        assert len(after["events"]) == 3
        page = client.get(f"/api/v1/matches/{MATCH_ID}/events").json()
        assert {e["id"] for e in page["items"]} == {e["id"] for e in after["events"]}
        messages = client.portal.call(
            client.app.state.store.after, MATCH_ID, before["streamCursor"]
        )
        assert len([m for m in messages if m.event == "match_event"]) == 3
        with client.stream(
            "GET",
            f"/api/v1/matches/{MATCH_ID}/stream",
            headers={"Last-Event-ID": "expired:1"},
        ) as response:
            response.read()
            assert "event: resync_required" in response.text
