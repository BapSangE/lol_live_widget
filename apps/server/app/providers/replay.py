from __future__ import annotations
import json
import time
from datetime import timedelta
from pathlib import Path
from app.models.contracts import MatchSummary, RawFrame, utcnow

class ReplayProvider:
    def __init__(self, step_seconds=10):
        fixture=Path(__file__).resolve().parents[4]/"fixtures/raw_frames/demo.json"
        self.frames=[RawFrame.model_validate(f) for f in json.loads(fixture.read_text())]
        self.started=time.monotonic()
        self.step=max(1,step_seconds)
        self.origin=utcnow()

    def _index(self):
        return min(int((time.monotonic()-self.started)/self.step),len(self.frames)-1)

    def _frame(self,index):
        return self.frames[index].model_copy(update={"source_timestamp":self.origin+timedelta(seconds=index*self.step)})

    async def list_matches(self):
        f=self._frame(self._index())
        return [MatchSummary(match_id=f.match_id,league=f.league,status=f.status,blue=f.blue,red=f.red,game_id=f.game_id,game_number=f.game_number)]

    async def get_match(self,match_id):
        m=(await self.list_matches())[0]
        if m.match_id!=match_id:raise KeyError(match_id)
        return m

    async def get_game_frames(self,game_id,after_source_timestamp=None):
        end=self._index()
        return [self._frame(i) for i in range(end+1) if self.frames[i].game_id==game_id and (after_source_timestamp is None or self._frame(i).source_timestamp>=after_source_timestamp)]

    async def get_game_details(self,game_id,timestamp):return None
    async def health(self):return {"availability":"replay","latencyMs":0,"errors":0}
    async def close(self):pass
