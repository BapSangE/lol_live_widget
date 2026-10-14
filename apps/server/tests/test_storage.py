from datetime import timedelta

import pytest
from app.storage.memory import CursorExpired, MemoryStore
from test_detector import BASE, frame


@pytest.mark.asyncio
async def test_duplicate_does_not_refresh_received_time_or_revision():
    s = MemoryStore()
    await s.ingest(frame(), now=BASE)
    await s.ingest(frame(), now=BASE + timedelta(seconds=40))
    snap = await s.sync("m", now=BASE + timedelta(seconds=40))
    assert snap.state.connection == "delayed"
    assert snap.state.revision == 1
    assert snap.state.received_at == BASE


@pytest.mark.asyncio
async def test_sync_cursor_replays_events_between_rest_and_stream():
    s = MemoryStore()
    await s.ingest(frame(), now=BASE)
    snap = await s.sync("m", now=BASE)
    await s.ingest(frame(10, barons=1), now=BASE)
    messages = await s.after("m", snap.stream_cursor)
    assert [m.event for m in messages] == ["state", "match_event"]
    assert messages[1].data["type"] == "BARON"
    again = await s.after("m", messages[-1].id)
    assert again == []


@pytest.mark.asyncio
async def test_expired_cursor_and_epoch_require_resync():
    s = MemoryStore(stream_capacity=2)
    await s.ingest(frame(), now=BASE)
    old = (await s.sync("m", now=BASE)).stream_cursor
    await s.ingest(frame(10, barons=1), now=BASE)
    await s.ingest(frame(20, blue_kills=1, barons=1), now=BASE)
    with pytest.raises(CursorExpired):
        await s.after("m", old)
    with pytest.raises(CursorExpired):
        await s.after("m", "another:2")


@pytest.mark.asyncio
async def test_game_revisions_reset_and_old_game_cannot_replace_new():
    s = MemoryStore()
    await s.ingest(frame(), now=BASE)
    await s.ingest(frame(10, blue_kills=1), now=BASE)
    await s.ingest(frame(20, game_id="g2"), now=BASE)
    assert (await s.sync("m", now=BASE)).state.revision == 1
    await s.ingest(frame(30), now=BASE)
    assert (await s.sync("m", now=BASE)).state.game_id == "g2"


@pytest.mark.asyncio
async def test_event_pagination_is_newest_first_and_bound_to_match():
    s = MemoryStore()
    await s.ingest(frame(), now=BASE)
    await s.ingest(frame(10, blue_kills=1), now=BASE)
    await s.ingest(frame(40, blue_kills=2), now=BASE)
    page = await s.events("m", 1, None)
    assert page.items[0].game_time_seconds == 40
    assert page.next_cursor
    older = await s.events("m", 1, page.next_cursor)
    assert older.items[0].game_time_seconds == 10
