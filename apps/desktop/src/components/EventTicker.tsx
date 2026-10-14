import type { MatchEvent } from '../types/contracts';
import { formatTime } from '../lib/policies';
export function EventTicker({event}:{event:MatchEvent}){
 return <span className="ticker" title={event.messageKo}><span className="ticker-mark" aria-hidden="true">◆</span><span className="ellipsis">{event.messageKo}</span><span className="time">{formatTime(event.gameTimeSeconds)}</span></span>;
}
