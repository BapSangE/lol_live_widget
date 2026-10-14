from __future__ import annotations
import asyncio
import logging
import random
import time
from datetime import timedelta
import httpx
from app.providers.base import AccessDenied
from app.models.contracts import utcnow

log=logging.getLogger(__name__)

def retry_delay(attempt:int)->float:
    return min(120,10*(2**min(attempt,4))+random.uniform(0,2))

class Poller:
    def __init__(self,provider,store,poll_seconds=10):
        self.provider,self.store=provider,store
        self.poll_seconds=poll_seconds
        self.matches=[]
        self.deadlines={}
        self.attempts={}
        self.last_timestamps={}
        self.blocked=False
        self.next_list=0.0
        self.updated_at=None

    async def update_matches(self):
        self.matches=await self.provider.list_matches()
        self.next_list=time.monotonic()+60

    async def collect(self,match):
        if match.game_id is None:return
        # Persisted schedule may not include games until getEventDetails is queried.
        after=self.last_timestamps.get(match.game_id)
        frames=await self.provider.get_game_frames(match.game_id,after-timedelta(seconds=20) if after else None)
        unique={f.source_timestamp:f for f in frames}
        for f in sorted(unique.values(),key=lambda f:f.source_timestamp):
            await self.store.ingest(f)
            if after is None or f.source_timestamp>after:after=f.source_timestamp
        if after:self.last_timestamps[match.game_id]=after
        self.updated_at=utcnow()

    async def tick(self):
        await self.store.refresh()
        if self.blocked:return
        now=time.monotonic()
        if now>=self.next_list:
            try:
                await self.update_matches()
                self.attempts['list']=0
                await self.store.set_error(None)
            except AccessDenied:
                self.blocked=True
                await self.store.set_error('access_denied')
                return
            except Exception as error:
                log.warning("match list unavailable (%s)",type(error).__name__)
                attempt=self.attempts.get('list',0)
                self.next_list=now+retry_delay(attempt)
                self.attempts['list']=attempt+1
                await self.store.set_error('rate_limited' if isinstance(error,httpx.HTTPStatusError) and error.response.status_code==429 else 'source_unavailable')
        for match in list(self.matches):
            if match.status not in ('live','ended'):continue
            key=match.match_id
            if now<self.deadlines.get(key,0):continue
            try:
                match=await self.provider.get_match(key)
                self.matches=[match if m.match_id==key else m for m in self.matches]
                await self.collect(match)
                self.deadlines[key]=now+self.poll_seconds
                self.attempts[key]=0
                await self.store.set_error(None)
                if match.status=='ended':self.deadlines[key]=now+86400
            except AccessDenied:
                self.blocked=True
                await self.store.set_error('access_denied')
                return
            except Exception as error:
                log.warning("game frames unavailable (%s)",type(error).__name__)
                attempt=self.attempts.get(key,0)
                self.deadlines[key]=now+retry_delay(attempt)
                self.attempts[key]=attempt+1
                await self.store.set_error('rate_limited' if isinstance(error,httpx.HTTPStatusError) and error.response.status_code==429 else 'source_unavailable')

    async def run(self):
        while True:
            await self.tick()
            await asyncio.sleep(1)
