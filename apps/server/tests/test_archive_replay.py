import pytest
from app.providers.replay import ReplayProvider


@pytest.mark.asyncio
async def test_archive_plays_original_timestamps_and_stops_at_sample_end(monkeypatch):
    monkeypatch.setenv(
        "REPLAY_FIXTURE", "fixtures/captures/lck-2026-09-13-gen-hle-game1/frames.json"
    )
    clock = [100.0]
    monkeypatch.setattr("app.providers.replay.time.monotonic", lambda: clock[0])
    provider = ReplayProvider()
    match = (await provider.list_matches())[0]
    assert match.league == "lck"
    first = await provider.get_game_frames(match.game_id)
    assert len(first) == 1
    assert first[0].source_timestamp.year == 2026
    assert first[0].blue.kills == first[0].red.kills == 3
    clock[0] += 30
    frames = await provider.get_game_frames(match.game_id)
    assert frames[-1].blue.kills == frames[-1].red.kills == 4
    assert (
        29
        < (frames[-1].source_timestamp - first[0].source_timestamp).total_seconds()
        <= 30
    )
    clock[0] += 100
    playback = (await provider.health())["playback"]
    assert playback["finished"] is True
    assert playback["durationSeconds"] == pytest.approx(69.263)
    assert (await provider.get_game_frames(match.game_id))[-1].status == "live"
