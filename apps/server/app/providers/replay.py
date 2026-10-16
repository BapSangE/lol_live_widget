from __future__ import annotations

import json
import os
import sys
import time
from bisect import bisect_right
from datetime import timedelta
from pathlib import Path

from app.models.contracts import MatchSummary, RawFrame, utcnow


class ReplayProvider:
    def __init__(self, step_seconds=10):
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[4]))
        self.archive = bool(os.environ.get("REPLAY_FIXTURE"))
        fixture = root / os.environ.get(
            "REPLAY_FIXTURE", "fixtures/raw_frames/demo.json"
        )
        self.frames = [
            RawFrame.model_validate(f) for f in json.loads(fixture.read_text())
        ]
        self.started = time.monotonic()
        self.step = max(1, step_seconds)
        self.origin = utcnow()
        self.offsets = [
            (f.source_timestamp - self.frames[0].source_timestamp).total_seconds()
            for f in self.frames
        ]
        if self.offsets != sorted(self.offsets):
            raise ValueError("Replay frames must be ordered by source timestamp")

    def _index(self):
        if self.archive:
            return max(
                0, bisect_right(self.offsets, time.monotonic() - self.started) - 1
            )
        return min(
            int((time.monotonic() - self.started) / self.step), len(self.frames) - 1
        )

    def _frame(self, index):
        if self.archive:
            return self.frames[index]
        return self.frames[index].model_copy(
            update={
                "source_timestamp": self.origin + timedelta(seconds=index * self.step)
            }
        )

    async def list_matches(self):
        f = self._frame(self._index())
        return [
            MatchSummary(
                match_id=f.match_id,
                league=f.league,
                status=f.status,
                blue=f.blue,
                red=f.red,
                game_id=f.game_id,
                game_number=f.game_number,
            )
        ]

    async def get_match(self, match_id):
        m = (await self.list_matches())[0]
        if m.match_id != match_id:
            raise KeyError(match_id)
        return m

    async def get_game_frames(self, game_id, after_source_timestamp=None):
        end = self._index()
        return [
            self._frame(i)
            for i in range(end + 1)
            if self.frames[i].game_id == game_id
            and (
                after_source_timestamp is None
                or self._frame(i).source_timestamp >= after_source_timestamp
            )
        ]

    async def get_game_details(self, game_id, timestamp):
        return None

    async def health(self):
        result = {"availability": "replay", "latencyMs": 0, "errors": 0}
        if self.archive:
            elapsed = time.monotonic() - self.started
            result["playback"] = {
                "kind": "archive",
                "elapsedSeconds": min(elapsed, self.offsets[-1]),
                "durationSeconds": self.offsets[-1],
                "finished": elapsed >= self.offsets[-1],
            }
        return result

    async def close(self):
        pass
