import { useEffect, useRef } from 'react';
import { useWidgetStore } from '../state/widgetStore';
import { demoEvents, demoFrames, demoMatch } from '../lib/demo';
import { parseSSE, wait } from '../lib/sse';
import type { MatchEvent, MatchState, MatchSummary, SyncSnapshot, UserSettings } from '../types/contracts';
export const serverURL=(import.meta.env.VITE_SERVER_URL as string|undefined)?.replace(/\/$/,'');
if(serverURL){const u=new URL(serverURL);if(u.protocol!=='https:'&&!(import.meta.env.DEV&&u.protocol==='http:'&&['127.0.0.1','localhost'].includes(u.hostname)))throw new Error('Server must use HTTPS');}
export function useMatchStream(settings:UserSettings,loaded:boolean){
 const preferences=useRef(settings);preferences.current=settings;
 useEffect(()=>{
  if(!loaded)return;
  const controller=new AbortController(),signal=controller.signal;
  const store=useWidgetStore;const mode=store.getState().mode;store.getState().reset();store.getState().setMode(mode);
  if(!serverURL){
   let index=0;store.setState({matches:[demoMatch],sourceMode:'replay',connected:true});
   store.getState().setState({...demoFrames[0],receivedAt:new Date().toISOString()});
   const timer=setInterval(()=>{
    index=Math.min(index+1,demoFrames.length-1);const frame={...demoFrames[index],receivedAt:new Date().toISOString()};
    store.getState().setState(frame);store.getState().addEvents(demoEvents.filter(e=>e.sourceRevision===frame.revision),true,preferences.current);
    if(index===demoFrames.length-1)clearInterval(timer);
   },10_000);
   return()=>{controller.abort();clearInterval(timer);};
  }
  const json=async<T,>(path:string):Promise<T>=>{const r=await fetch(`${serverURL}/api/v1${path}`,{signal});if(!r.ok)throw new Error(`HTTP ${r.status}`);return await r.json() as T;};
  let selected:string|null=null,cursor='',synchronized=false,attempt=0,epoch='';
  const discover=async()=>{
   const matches=await json<MatchSummary[]>('/matches?league=worlds');if(signal.aborted)return;
   store.setState({matches});
   const preferred=preferences.current.preferredMatchId;
   const choice=matches.find(m=>m.matchId===preferred&&m.status!=='scheduled')||matches.find(m=>m.status==='live');
   selected=choice?.matchId||null;
  };
  const run=async()=>{
   while(!signal.aborted){
    try{
     if(!selected){await discover();if(!selected){store.setState({notice:null,connected:true,state:null});await wait(60_000,signal);continue;}}
     if(!synchronized){
      const snap=await json<SyncSnapshot>(`/matches/${encodeURIComponent(selected)}/sync`);if(signal.aborted)return;
      const nextEpoch=snap.streamCursor.split(':')[0];
      const restarted=Boolean(epoch&&epoch!==nextEpoch);epoch=nextEpoch;
      store.setState({...(restarted?{events:[]}:{}),ticker:null,tickerUntil:0,state:snap.state,sourceMode:snap.sourceMode,notice:restarted?'서버 재시작으로 로그가 초기화됨':null});
      store.getState().addEvents(snap.events,false,preferences.current);cursor=snap.streamCursor;synchronized=true;
     }
     const response=await fetch(`${serverURL}/api/v1/matches/${encodeURIComponent(selected)}/stream`,{signal,headers:{'Last-Event-ID':cursor}});
     if(!response.ok||!response.body)throw new Error(`Stream HTTP ${response.status}`);
     store.setState({connected:true});
     let resync=false;
     for await(const message of parseSSE(response.body)){
      if(signal.aborted)return;
      if(message.event==='resync_required'){synchronized=false;resync=true;break;}
      if(message.event==='state')store.getState().setState(JSON.parse(message.data) as MatchState);
      else if(message.event==='match_event')store.getState().addEvents([JSON.parse(message.data) as MatchEvent],true,preferences.current);
      if(message.id)cursor=message.id;
      attempt=0;
     }
     if(resync){attempt=0;continue;}
     throw new Error('Stream ended');
    }catch(error){
     if(signal.aborted)return;
     console.warn('Match connection unavailable',error);store.setState({connected:false,notice:'재연결 중'});
     await wait([2,4,8,16,30][Math.min(attempt++,4)]*1000,signal).catch(()=>{});
     // Every reconnect REST-syncs first; historical events never trigger a ticker.
     synchronized=false;
    }
   }
  };
  void run().catch(error=>{if(!signal.aborted)console.error(error);});
  return()=>controller.abort();
 },[loaded,settings.preferredMatchId]);
}
