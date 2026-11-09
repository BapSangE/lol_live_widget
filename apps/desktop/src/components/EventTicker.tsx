import type { MatchEvent } from '../types/contracts';
import { formatGameTime, estimatedClockHint } from '../lib/policies';
export function EventTicker({ event }: { event: MatchEvent }) {
  return (
    <span className="ticker" title={event.messageKo}>
      <span className="ticker-mark" aria-hidden="true">
        ◆
      </span>
      <span className="ellipsis">{event.messageKo}</span>
      <span
        className="time"
        title={
          event.gameTimeSeconds == null && event.estimatedGameTimeSeconds != null
            ? estimatedClockHint
            : undefined
        }
      >
        {formatGameTime(event.gameTimeSeconds, event.estimatedGameTimeSeconds)}
      </span>
    </span>
  );
}
