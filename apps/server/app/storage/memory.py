from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from app.events.detector import Detector
from app.models.contracts import EventsPage, MatchState, RawFrame, SyncSnapshot, utcnow


class CursorExpired(Exception):
    pass


@dataclass(frozen=True)
class StreamMessage:
    id: str
    event: str
    data: dict
    sequence: int


class MemoryStore:
    def __init__(self, source_mode="replay", stream_capacity=1000):
        self.source_mode = source_mode
        self.epoch = uuid4().hex
        self.sequence = 0
        self.capacity = stream_capacity
        self.lock = asyncio.Lock()
        self.states = {}
        self.frames = {}
        self.detectors = {}
        self.logs = {}
        self.streams = {}
        self.floors = {}
        self.retired_games = {}
        self.source_error = None

    def _push(self, match_id, kind, data):
        self.sequence += 1
        message = StreamMessage(
            f"{self.epoch}:{self.sequence}", kind, data, self.sequence
        )
        stream = self.streams.setdefault(match_id, deque())
        if len(stream) >= self.capacity:
            self.floors[match_id] = stream.popleft().sequence
        stream.append(message)

    async def ingest(self, frame: RawFrame, now: datetime | None = None):
        now = now or utcnow()
        async with self.lock:
            match = frame.match_id
            previous = self.frames.get(match)
            if frame.game_id in self.retired_games.get(match, set()):
                return
            if previous and frame.game_id == previous.game_id:
                if (
                    frame.source_timestamp < previous.source_timestamp
                    or frame == previous
                ):
                    return
            elif previous:
                if frame.source_timestamp <= previous.source_timestamp:
                    return
                self.retired_games.setdefault(match, set()).add(previous.game_id)
                self.detectors[match] = Detector()
            advancing = (
                previous is None or frame.source_timestamp > previous.source_timestamp
            )
            previous_state = self.states.get(match)
            revision = (
                previous_state.revision + 1
                if previous_state and previous_state.game_id == frame.game_id
                else 1
            )
            detector = self.detectors.setdefault(match, Detector())
            events = detector.process(frame, revision)
            self.frames[match] = frame
            state = MatchState(
                match_id=match,
                game_id=frame.game_id,
                status=frame.status,
                connection="live",
                league=frame.league,
                blue=frame.blue,
                red=frame.red,
                game_number=frame.game_number,
                game_time_seconds=frame.game_time_seconds,
                source_timestamp=frame.source_timestamp,
                received_at=now if advancing else previous_state.received_at,
                revision=revision,
                source_error=self.source_error,
            )
            state = self._freshness(state, now)
            self.states[match] = state
            self._push(match, "state", state.model_dump(mode="json", by_alias=True))
            log = self.logs.setdefault(match, deque(maxlen=1000))
            known = {e.id for e in log}
            for event in events:
                if event.id not in known:
                    log.appendleft(event)
                    self._push(
                        match,
                        "match_event",
                        event.model_dump(mode="json", by_alias=True),
                    )
                    known.add(event.id)

    def _freshness(self, state, now):
        age = max(0, (now - state.received_at).total_seconds())
        connection = "offline" if age > 120 else ("delayed" if age > 30 else "live")
        if state.status == "ended":
            connection = "offline"  # finished games are never labelled live
        if self.source_error == "access_denied":
            connection = "offline"
        elif self.source_error:
            connection = "delayed" if connection == "live" else connection
        return state.model_copy(
            update={"connection": connection, "source_error": self.source_error}
        )

    async def refresh(self, now=None):
        now = now or utcnow()
        async with self.lock:
            for match, state in list(self.states.items()):
                if state.status == "ended" and now - state.received_at > timedelta(
                    hours=24
                ):
                    for mapping in (
                        self.states,
                        self.frames,
                        self.detectors,
                        self.logs,
                        self.streams,
                        self.floors,
                        self.retired_games,
                    ):
                        mapping.pop(match, None)
                    continue
                updated = self._freshness(state, now)
                if updated != state:
                    self.states[match] = updated
                    self._push(
                        match, "state", updated.model_dump(mode="json", by_alias=True)
                    )

    async def set_error(self, error):
        self.source_error = error
        await self.refresh()

    async def sync(self, match_id, now=None):
        async with self.lock:
            state = self._freshness(self.states[match_id], now or utcnow())
            return SyncSnapshot(
                state=state,
                events=list(self.logs.get(match_id, []))[:50],
                stream_cursor=f"{self.epoch}:{self.sequence}",
                source_mode=self.source_mode,
            )

    async def after(self, match_id, cursor):
        async with self.lock:
            try:
                epoch, value = cursor.split(":", 1)
                sequence = int(value)
            except (ValueError, AttributeError):
                raise CursorExpired() from None
            if (
                epoch != self.epoch
                or sequence < self.floors.get(match_id, 0)
                or sequence > self.sequence
                or sequence < 0
            ):
                raise CursorExpired()
            return [m for m in self.streams.get(match_id, []) if m.sequence > sequence]

    async def events(self, match_id, limit=50, before=None):
        async with self.lock:
            if match_id not in self.states:
                raise KeyError(match_id)
            items = list(self.logs.get(match_id, []))
            if before:
                index = next((i for i, e in enumerate(items) if e.id == before), None)
                if index is None:
                    raise CursorExpired()
                items = items[index + 1 :]
            selected = items[:limit]
            return EventsPage(
                items=selected,
                next_cursor=selected[-1].id if len(items) > limit else None,
            )
