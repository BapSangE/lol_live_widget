import pytest
import httpx
from app.collectors.poller import Poller, retry_delay
from app.providers.base import AccessDenied
from app.providers.lolesports import LoLEsportsProvider
from app.storage.memory import MemoryStore
from app.models.contracts import MatchSummary
from test_detector import frame

@pytest.mark.asyncio
async def test_access_denied_stops_source_calls():
    class Denied:
        calls=0
        async def list_matches(self):self.calls+=1;raise AccessDenied()
    p=Denied();s=MemoryStore('live');poller=Poller(p,s)
    await poller.tick();await poller.tick()
    assert p.calls==1 and poller.blocked and s.source_error=='access_denied'

@pytest.mark.asyncio
async def test_collector_requests_overlap_and_sorts_deduplicates():
    class Source:
        requests=[]
        async def get_game_frames(self,game_id,after):self.requests.append(after);return [frame(10,blue_kills=1),frame(),frame(10,blue_kills=1)]
    source=Source();s=MemoryStore();p=Poller(source,s)
    m=MatchSummary(match_id='m',blue=frame().blue,red=frame().red,game_id='g')
    await p.collect(m);await p.collect(m)
    snap=await s.sync('m')
    assert snap.state.revision==2
    assert [e.type for e in snap.events]==['KILL_DELTA']
    assert (p.last_timestamps['g']-source.requests[1]).total_seconds()==20

@pytest.mark.asyncio
async def test_source_nulls_and_metadata_team_mapping():
    async def response(request):
        return httpx.Response(200,json={'gameMetadata':{'blueTeamMetadata':{'esportsTeamId':'gen'},'redTeamMetadata':{'esportsTeamId':'t1'}},'frames':[{'rfc460Timestamp':'2026-10-14T00:00:00Z','gameState':'in_game','blueTeam':{'totalKills':4,'dragons':['cloud']},'redTeam':{}}]})
    client=httpx.AsyncClient(transport=httpx.MockTransport(response))
    source=LoLEsportsProvider('test-key',True,client)
    source.game_matches['g']=MatchSummary(match_id='m',blue=frame().blue,red=frame().red,game_id='g')
    frames=await source.get_game_frames('g',None)
    assert frames[0].blue.id=='gen'
    assert frames[0].blue.kills==4 and frames[0].blue.gold is None
    assert frames[0].red.kills is None and frames[0].game_time_seconds is None
    await source.close()

def test_backoff_is_bounded():
    assert 10<=retry_delay(0)<=12
    assert retry_delay(99)==120
