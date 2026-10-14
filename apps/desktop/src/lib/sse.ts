export interface SSEMessage {event:string;id:string;data:string}
export async function* parseSSE(stream:ReadableStream<Uint8Array>):AsyncGenerator<SSEMessage> {
 const reader=stream.getReader(),decoder=new TextDecoder();
 let buffer='',event='message',id='',data:string[]=[];
 try{
  while(true){
   const result=await reader.read();buffer+=decoder.decode(result.value,{stream:!result.done});
   let newline:number;
   while((newline=buffer.indexOf('\n'))>=0){
    let line=buffer.slice(0,newline);buffer=buffer.slice(newline+1);if(line.endsWith('\r'))line=line.slice(0,-1);
    if(line===''){
     if(data.length)yield {event,id,data:data.join('\n')};
     event='message';data=[];continue;
    }
    if(line.startsWith(':'))continue;
    const colon=line.indexOf(':');const key=colon<0?line:line.slice(0,colon);let value=colon<0?'':line.slice(colon+1);if(value.startsWith(' '))value=value.slice(1);
    if(key==='event')event=value;else if(key==='id'&&!value.includes('\0'))id=value;else if(key==='data')data.push(value);
   }
   if(result.done)break;
   if(buffer.length>1_000_000)throw new Error('SSE message too large');
  }
 }finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
}
export function wait(ms:number,signal:AbortSignal):Promise<void>{
 return new Promise((resolve,reject)=>{
  if(signal.aborted){reject(new DOMException('Aborted','AbortError'));return;}
  const abort=()=>{clearTimeout(timer);reject(new DOMException('Aborted','AbortError'));};
  const timer=setTimeout(()=>{signal.removeEventListener('abort',abort);resolve();},ms);
  signal.addEventListener('abort',abort,{once:true});
 });
}
