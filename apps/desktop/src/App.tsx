import { useCallback, useEffect, useState } from 'react';
import { listen } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/core';
import { native, setAutostart } from './lib/native';
import { deriveConnection } from './lib/policies';
import { useWidgetStore } from './state/widgetStore';
import { useSettings } from './hooks/useSettings';
import { useOpacity } from './hooks/useOpacity';
import { useWindowGeometry } from './hooks/useWindowGeometry';
import { serverURL, useMatchStream } from './hooks/useMatchStream';
import { ScoreBar } from './components/ScoreBar';
import { ExpandedPanel } from './components/ExpandedPanel';
import { SettingsPanel } from './components/SettingsPanel';
import type { EventsPage, UserSettings } from './types/contracts';
export default function App(){
 const {settings,setSettings,loaded,error,setError}=useSettings();const widget=useWidgetStore();const [hovered,setHovered]=useState(false),[now,setNow]=useState(Date.now());
 const report=useCallback((message:string)=>setError(message),[setError]);
 const {opacity}=useOpacity(settings,hovered,report);
 useWindowGeometry(widget.mode,settings,loaded,setSettings,report);useMatchStream(settings,loaded);
 useEffect(()=>{const timer=setInterval(()=>{const time=Date.now();setNow(time);useWidgetStore.getState().expire(time);},250);return()=>clearInterval(timer);},[]);
 useEffect(()=>{const escape=(e:KeyboardEvent)=>{if(e.key==='Escape')useWidgetStore.getState().setMode('compact');};window.addEventListener('keydown',escape);return()=>window.removeEventListener('keydown',escape);},[]);
 useEffect(()=>{
  if(!native)return;
  const off:Array<()=>void>=[];let stopped=false;
  void listen('open-settings',()=>useWidgetStore.getState().setMode('settings')).then(f=>{if(stopped)f();else off.push(f);});
  void listen<boolean>('always-on-top-changed',e=>setSettings(s=>({...s,alwaysOnTop:e.payload}))).then(f=>{if(stopped)f();else off.push(f);});
  return()=>{stopped=true;off.forEach(f=>f());};
 },[setSettings]);
 const change=async(patch:Partial<UserSettings>)=>{
  try{if(patch.launchAtLogin!==undefined)await setAutostart(patch.launchAtLogin);if(patch.alwaysOnTop!==undefined&&native)await invoke('apply_always_on_top',{enabled:patch.alwaysOnTop});setSettings(s=>({...s,...patch}));setError(null);}
  catch(err){console.error(err);setError('설정을 적용할 수 없음');}
 };
 const state=widget.state;
 const age=state?(now-Date.parse(state.receivedAt))/1000:Infinity;
 const aged=state?deriveConnection(age):'offline';
 const connection=!widget.connected&&aged==='live'?'delayed':aged;
 const sourceError=state?.sourceError;
 const status=sourceError==='access_denied'?'데이터 접근 불가':sourceError==='rate_limited'?'갱신 일시 지연':state?.status==='ended'?'경기 종료':!widget.connected?'재연결 중':connection==='delayed'?'데이터 지연':connection==='offline'?'연결 끊김':widget.sourceMode==='replay'?'모의 데이터':'라이브';
 const shownState=state?{...state,connection:state.status==='ended'?'offline' as const:sourceError?state.connection:connection}:null;
 const notice=error||widget.notice||(connection!=='live'&&state?.status==='live'?status:null);
 const theme=settings.theme==='system'?(window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):settings.theme;
 const loadMore=async()=>{
  if(!serverURL||!state)return;
  try{const before=widget.nextCursor||widget.events[widget.events.length-1]?.id;if(!before)return;
   const r=await fetch(`${serverURL}/api/v1/matches/${encodeURIComponent(state.matchId)}/events?limit=100&before=${encodeURIComponent(before)}`);if(!r.ok)throw new Error('History unavailable');
   const page=await r.json() as EventsPage;if(useWidgetStore.getState().state?.matchId!==state.matchId)return;useWidgetStore.getState().addEvents(page.items,false,settings);useWidgetStore.setState({nextCursor:page.nextCursor});
  }catch(err){console.warn(err);setError('이전 기록을 불러올 수 없음');}
 };
 return <main className={`widget ${widget.mode} theme-${theme}`} style={{opacity}} onPointerEnter={()=>setHovered(true)} onPointerLeave={()=>setHovered(false)}>
  {widget.mode==='compact'?<><ScoreBar state={shownState} ticker={widget.ticker} status={status} onExpand={()=>widget.setMode('expanded')}/>{widget.sourceMode==='replay'&&<span className="compact-mode-label" title="모의 데이터">DEMO</span>}{notice&&<span className="compact-notice" title={notice} aria-label={notice}>!</span>}</>:widget.mode==='expanded'?<ExpandedPanel state={shownState} events={widget.events} status={status} replay={widget.sourceMode==='replay'} matches={widget.matches} onCollapse={()=>widget.setMode('compact')} onSettings={()=>widget.setMode('settings')} onLoadMore={()=>void loadMore()} hasMore={Boolean(serverURL&&widget.events.length>=50)}/>:<SettingsPanel settings={settings} matches={widget.matches} onChange={patch=>void change(patch)} onBack={()=>widget.setMode('expanded')}/>}
  {notice&&widget.mode!=='compact'&&<div className="notice" role="status">{notice}<button aria-label="안내 닫기" onClick={()=>{setError(null);useWidgetStore.setState({notice:null});}}>×</button></div>}
 </main>;
}
