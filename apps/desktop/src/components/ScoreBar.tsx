import { getCurrentWindow } from '@tauri-apps/api/window';
import { native } from '../lib/native';
import { formatTime } from '../lib/policies';
import type { MatchEvent, MatchState } from '../types/contracts';
import { EventTicker } from './EventTicker';
interface Props {
  state: MatchState | null;
  ticker: MatchEvent | null;
  status: string;
  onExpand: () => void;
}
export function ScoreBar({ state, ticker, status, onExpand }: Props) {
  return (
    <div className="scorebar">
      <span
        className="drag-handle"
        title="드래그하여 이동"
        aria-label="위젯 이동"
        onPointerDown={(e) => {
          if (e.button === 0 && native) {
            e.preventDefault();
            void getCurrentWindow().startDragging().catch(console.error);
          }
        }}
      >
        ⠿
      </span>
      <button className="score-content" aria-label="경기 상세 열기" onClick={onExpand}>
        <span className={`status-dot ${state?.connection || 'offline'}`} title={status} />
        {ticker ? (
          <EventTicker event={ticker} />
        ) : state ? (
          <span className="score-line">
            <span className="team-name">{state.blue.shortName}</span>
            <strong>
              {state.blue.seriesWins} : {state.red.seriesWins}
            </strong>
            <span className="team-name">{state.red.shortName}</span>
            <span className="time">{formatTime(state.gameTimeSeconds)}</span>
          </span>
        ) : (
          <span className="empty-copy">진행 중 경기 없음</span>
        )}
        <span className="expand-chevron" aria-hidden="true">
          ⌃
        </span>
      </button>
    </div>
  );
}
