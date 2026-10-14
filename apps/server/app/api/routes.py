from __future__ import annotations
import asyncio
import json
import time
from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from app.models.contracts import EventsPage, MatchState, MatchSummary, SyncSnapshot, utcnow
from app.storage.memory import CursorExpired

router=APIRouter(prefix='/api/v1')

@router.get('/health')
async def health(request:Request):
    p=request.app.state.poller
    source=await p.provider.health()
    return {'status':'degraded' if p.store.source_error else 'ok','sourceStatus':p.store.source_error or ('replay' if p.store.source_mode=='replay' else source['availability']),'updatedAt':p.updated_at or utcnow(),'source':source}

@router.get('/matches',response_model=list[MatchSummary])
async def matches(request:Request,league:str='worlds',status:str|None=None):
    return [m for m in request.app.state.poller.matches if m.league==league and (status is None or m.status==status)]

async def snapshot(request,match_id):
    try:return await request.app.state.store.sync(match_id)
    except KeyError:raise HTTPException(404,'Match state unavailable') from None

@router.get('/matches/{match_id}/state',response_model=MatchState)
async def state(request:Request,match_id:str):return (await snapshot(request,match_id)).state

@router.get('/matches/{match_id}/sync',response_model=SyncSnapshot)
async def sync(request:Request,match_id:str):return await snapshot(request,match_id)

@router.get('/matches/{match_id}/events',response_model=EventsPage)
async def events(request:Request,match_id:str,limit:int=Query(50,ge=1,le=100),before:str|None=None):
    try:return await request.app.state.store.events(match_id,limit,before)
    except KeyError:raise HTTPException(404,'Match state unavailable') from None
    except CursorExpired:raise HTTPException(410,'Event cursor expired; resynchronize') from None

@router.get('/matches/{match_id}/stream')
async def stream(request:Request,match_id:str,last_event_id:str|None=Header(None)):
    snap=await snapshot(request,match_id)
    async def generate():
        cursor=last_event_id or snap.stream_cursor
        if not last_event_id:
            yield f'event: state\nid: {cursor}\ndata: {snap.state.model_dump_json(by_alias=True)}\n\n'
        heartbeat=time.monotonic()
        while not await request.is_disconnected():
            try:messages=await request.app.state.store.after(match_id,cursor)
            except CursorExpired:
                yield 'event: resync_required\ndata: {}\n\n'
                return
            for message in messages:
                yield f'event: {message.event}\nid: {message.id}\ndata: {json.dumps(message.data,ensure_ascii=False)}\n\n'
                cursor=message.id
            if time.monotonic()-heartbeat>=15:
                yield ': keepalive\n\n'
                heartbeat=time.monotonic()
            await asyncio.sleep(.25)
    return StreamingResponse(generate(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
