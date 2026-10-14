import { it, expect } from 'vitest';
import { parseSSE } from '../lib/sse';
import { useWidgetStore } from '../state/widgetStore';
import { defaults } from '../lib/policies';
import type { MatchEvent } from '../types/contracts';
it('parses chunked UTF-8 multiline SSE and ignores heartbeats',async()=>{
 const text=': keepalive\r\n\r\nevent: match_event\r\nid: e:2\r\ndata: {"messageKo":\r\ndata: "바론"}\r\n\r\n';
 const bytes=new TextEncoder().encode(text);
 const stream=new ReadableStream<Uint8Array>({start(c){for(let i=0;i<bytes.length;i+=3)c.enqueue(bytes.slice(i,i+3));c.close();}});
 const result=[];for await(const m of parseSSE(stream))result.push(m);
 expect(result).toEqual([{event:'match_event',id:'e:2',data:'{"messageKo":\n"바론"}'}]);
});
it('does not alert historical events, clears ticker on expansion and deduplicates',()=>{
 useWidgetStore.getState().reset();
 const event:MatchEvent={id:'a',matchId:'m',gameId:'g',type:'BARON',gameTimeSeconds:0,occurredAt:null,observedAt:new Date().toISOString(),teamId:null,priority:'important',messageKo:'바론',confidence:'derived',sourceRevision:1};
 useWidgetStore.getState().addEvents([event],false,defaults);
 expect(useWidgetStore.getState().ticker).toBeNull();
 useWidgetStore.getState().addEvents([{...event,id:'b'}],true,defaults);
 expect(useWidgetStore.getState().ticker?.id).toBe('b');
 useWidgetStore.getState().setMode('expanded');
 expect(useWidgetStore.getState().ticker).toBeNull();
 useWidgetStore.getState().addEvents([event],true,defaults);
 expect(useWidgetStore.getState().events).toHaveLength(2);
});
