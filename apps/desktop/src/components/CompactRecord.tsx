import { formatTime } from '../lib/policies';
import type { MatchEvent, MatchState } from '../types/contracts';

interface Props {
  state: MatchState | null;
  events: MatchEvent[];
  onExpand: () => void;
}

export function CompactRecord({ state, events, onExpand }: Props) {
  const latest = state
    ? events.find((event) => event.matchId === state.matchId && event.gameId === state.gameId)
    : undefined;
  const message = latest?.messageKo || (state ? '새로운 경기 기록을 기다리는 중' : '진행 중 경기 없음');
  return (
    <button
      className={`compact-record${latest ? '' : ' empty'}`}
      aria-label="최근 경기 기록 열기"
      title={message}
      onClick={onExpand}
    >
      <span className="compact-record-label">최근</span>
      {latest?.gameTimeSeconds != null && (
        <time>{formatTime(latest.gameTimeSeconds)}</time>
      )}
      <span className="compact-record-message" aria-live="polite" aria-atomic="true">
        {message}
      </span>
    </button>
  );
}
