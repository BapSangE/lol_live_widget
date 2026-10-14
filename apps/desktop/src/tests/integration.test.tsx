import { afterEach, it, expect, vi } from 'vitest';
import { act, cleanup, renderHook } from '@testing-library/react';
import { useWidgetStore } from '../state/widgetStore';
import { defaults } from '../lib/policies';
import { demoFrames } from '../lib/demo';
import type { MatchEvent } from '../types/contracts';
afterEach(()=>{cleanup();vi.useRealTimers();vi.unstubAllGlobals();vi.unstubAllEnvs();useWidgetStore.getState().reset();});
it('new events after reconnection can alert while bootstrap history cannot',async()=>{
 vi.useFakeTimers();vi.stubEnv('VITE_SERVER_URL','http://127.0.0.1:8000');
 const {useMatchStream}=await import('../hooks/useMatchStream');
 let connections=0;
 const event:MatchEvent={id:'new-baron',matchId:'demo-worlds',gameId:'demo-game-4',type:'BARON',gameTimeSeconds:1452,occurredAt:null,observedAt:new Date().toISOString(),teamId:'t1',priority:'important',messageKo:'T1 바론 획득',confidence:'derived',sourceRevision:2};
 vi.stubGlobal('fetch',async(url:string)=>{
  if(url.includes('/matches?'))return new Response(JSON.stringify([{matchId:'demo-worlds',status:'live',league:'worlds'}]));
  if(url.endsWith('/sync'))return new Response(JSON.stringify({state:demoFrames[0],events:[],streamCursor:'epoch:1',sourceMode:'replay'}));
  connections++;
  return new Response(new ReadableStream({start(c){if(connections===1)c.close();else c.enqueue(new TextEncoder().encode(`event: match_event\nid: epoch:2\ndata: ${JSON.stringify(event)}\n\n`));}}));
 });
 renderHook(()=>useMatchStream(defaults,true));
 await act(async()=>{for(let i=0;i<20;i++)await Promise.resolve();});
 await act(async()=>{await vi.advanceTimersByTimeAsync(2000);for(let i=0;i<20;i++)await Promise.resolve();});
 expect(connections).toBe(2);
 expect(useWidgetStore.getState().events[0].id).toBe('new-baron');
 expect(useWidgetStore.getState().ticker?.id).toBe('new-baron');
});
