from __future__ import annotations
from datetime import datetime, timedelta
import time
import httpx
from app.models.contracts import MatchSummary, RawFrame, TeamState
from app.providers.base import AccessDenied

class LoLEsportsProvider:
    """Opt-in unofficial adapter; credentials never enter client or repository."""
    def __init__(self,key:str,approved:bool,client:httpx.AsyncClient|None=None):
        self.key=key
        self.approved=approved
        self.client=client or httpx.AsyncClient(timeout=5)
        self.matches={}
        self.game_matches={}
        self.latency=0
        self.errors=0
        self.last_error=None

    async def _request(self,path,params=None,feed=False):
        if not self.approved or not self.key:
            self.last_error="access_denied"
            raise AccessDenied("Live source requires documented approval and server credentials")
        base="https://feed.lolesports.com/livestats/v1" if feed else "https://esports-api.lolesports.com/persisted/gw"
        started=time.monotonic()
        try:
            response=await self.client.get(f"{base}/{path}",params=params,headers={"x-api-key":self.key})
            if response.status_code in (401,403):
                raise AccessDenied("Source rejected access")
            response.raise_for_status()
            result=response.json()
            self.last_error=None
            return result
        except (httpx.HTTPError,ValueError,AccessDenied):
            self.errors+=1
            raise
        finally:
            self.latency=round((time.monotonic()-started)*1000)

    @staticmethod
    def _summary(event):
        match=event.get("match",{})
        teams=match.get("teams",[])
        if len(teams)!=2:return None
        def team(t):
            return TeamState(id=str(t["id"]),name=t.get("name",str(t["id"])),short_name=t.get("code") or t.get("name",str(t["id"]))[:6],series_wins=(t.get("result") or {}).get("gameWins",0))
        status={"inProgress":"live","completed":"ended","unstarted":"scheduled"}.get(event.get("state"),"unknown")
        games=match.get("games",[])
        game=next((g for g in games if g.get("state")=="inProgress"),None)
        if game is None:
            game=next((g for g in reversed(games) if g.get("state")=="completed"),None)
        return MatchSummary(match_id=str(event["id"]),league="worlds" if "world" in (event.get("league",{}).get("slug","")+event.get("league",{}).get("name","")).lower() else event.get("league",{}).get("slug","unknown"),status=status,blue=team(teams[0]),red=team(teams[1]),game_id=str(game["id"]) if game else None,game_number=game.get("number") if game else None,scheduled_at=event.get("startTime"))

    async def list_matches(self):
        live=await self._request("getLive",{"hl":"en-US"})
        schedule=await self._request("getSchedule",{"hl":"en-US"})
        raw=live.get("data",{}).get("schedule",{}).get("events",[])+schedule.get("data",{}).get("schedule",{}).get("events",[])
        result={}
        for event in raw:
            if event.get("type") not in (None,"match"):continue
            summary=self._summary(event)
            if summary and summary.league=="worlds":result.setdefault(summary.match_id,summary)
        self.matches=result
        for m in result.values():
            if m.game_id:self.game_matches[m.game_id]=m
        return list(result.values())

    async def get_match(self,match_id):
        payload=await self._request("getEventDetails",{"hl":"en-US","id":match_id})
        event=payload.get("data",{}).get("event")
        summary=self._summary(event or {})
        if summary is None:raise ValueError("Unsupported match details")
        self.matches[match_id]=summary
        if summary.game_id:self.game_matches[summary.game_id]=summary
        return summary

    @staticmethod
    def _stats(raw,team):
        participants=raw.get("participants",[])
        def number(field,participant_field=None):
            value=raw.get(field)
            if value is None and participants and participant_field and all(p.get(participant_field) is not None for p in participants):
                value=sum(p[participant_field] for p in participants)
            return value if isinstance(value,int) and not isinstance(value,bool) and value>=0 else None
        dragons=raw.get("dragons")
        return team.model_copy(update={"kills":number("totalKills","kills"),"gold":number("totalGold","totalGold"),"towers":number("towers"),"dragons":len(dragons) if isinstance(dragons,list) else number("dragons"),"barons":number("barons")})

    async def get_game_frames(self,game_id,after_source_timestamp=None):
        params={}
        if after_source_timestamp:
            # Feed timestamps align to ten-second windows. Caller requests overlap.
            aligned=after_source_timestamp-timedelta(seconds=after_source_timestamp.second%10,microseconds=after_source_timestamp.microsecond)
            params["startingTime"]=aligned.isoformat().replace("+00:00","Z")
        payload=await self._request(f"window/{game_id}",params,feed=True)
        summary=self.game_matches[game_id]
        metadata=payload.get("gameMetadata",{})
        result=[]
        for raw in payload.get("frames",[]):
            if not raw.get("rfc460Timestamp"):continue
            def mapped(side,fallback):
                id=str(metadata.get(f"{side}TeamMetadata",{}).get("esportsTeamId",fallback.id))
                return next((t for t in (summary.blue,summary.red) if t.id==id),fallback)
            blue=self._stats(raw.get("blueTeam",{}),mapped("blue",summary.blue))
            red=self._stats(raw.get("redTeam",{}),mapped("red",summary.red))
            game_time=raw.get("gameTimeSeconds")
            result.append(RawFrame(match_id=summary.match_id,game_id=game_id,source_timestamp=raw["rfc460Timestamp"],game_time_seconds=game_time if isinstance(game_time,int) else None,blue=blue,red=red,status="ended" if raw.get("gameState")=="finished" else summary.status,league=summary.league,game_number=summary.game_number))
        return result

    async def get_game_details(self,game_id,timestamp):
        return await self._request(f"details/{game_id}",{"startingTime":timestamp.isoformat().replace("+00:00","Z")},feed=True)
    async def health(self):return {"availability":self.last_error or "available","latencyMs":self.latency,"errors":self.errors}
    async def close(self):await self.client.aclose()
