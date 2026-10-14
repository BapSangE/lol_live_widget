import { useEffect, useRef, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { effectiveOpacity } from '../lib/policies';
import { native } from '../lib/native';
import type { UserSettings } from '../types/contracts';
export function useOpacity(settings:UserSettings,hovered:boolean,onError:(message:string)=>void){
 const [backend,setBackend]=useState<'css'|'native'>('css');const [applied,setApplied]=useState(65);const generation=useRef(0),last=useRef(65);
 useEffect(()=>{if(native)void invoke<'css'|'native'>('opacity_backend').then(setBackend).catch(()=>{});},[]);
 const requested=effectiveOpacity(settings.opacityPercent,settings.brightenOnHover,hovered);
 useEffect(()=>{
  const token=++generation.current;
  if(backend==='css'){setApplied(requested);last.current=requested;return;}
  const start=last.current;
  void(async()=>{
   try{
    for(let step=1;step<=10&&token===generation.current;step++){
     const percent=Math.round(start+(requested-start)*step/10);
     await invoke('set_window_opacity',{percent});last.current=percent;setApplied(percent);
     await new Promise(resolve=>setTimeout(resolve,15));
    }
   }catch(error){console.error('Opacity unavailable',error);onError('불투명도 조절을 적용할 수 없음');}
  })();
  return()=>{generation.current++;};
 },[requested,backend,onError]);
 return {opacity:backend==='css'?applied/100:1,backend};
}
