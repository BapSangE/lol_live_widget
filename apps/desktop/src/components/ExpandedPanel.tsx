import { useEffect, useRef, useState } from 'react';
import { formatTime, stat } from '../lib/policies';
import type { MatchEvent, MatchState, MatchSummary } from '../types/contracts';
const names: Record<string, string> = {
  KILL_DELTA: '킬',
  MULTIKILL_WINDOW: '킬 교환',
  DRAGON: '드래곤',
  BARON: '바론',
  ELDER: '장로',
  DRAGON_SOUL: '영혼',
  TOWER: '타워',
  GOLD_LEAD_CHANGE: '골드',
  GAME_END: '종료',
};
interface Props {
  state: MatchState | null;
  events: MatchEvent[];
  status: string;
  replay: boolean;
  matches: MatchSummary[];
  onCollapse: () => void;
  onSettings: () => void;
  onLoadMore?: () => void;
  hasMore?: boolean;
}
export function ExpandedPanel({
  state,
  events,
  status,
  replay,
  matches,
  onCollapse,
  onSettings,
  onLoadMore,
  hasMore,
}: Props) {
  const scroller = useRef<HTMLDivElement>(null),
    atTop = useRef(true);
  const last = useRef('');
  const [newCount, setNewCount] = useState(0);
  useEffect(() => {
    if (events[0]?.id !== last.current && !atTop.current) setNewCount((n) => n + 1);
    last.current = events[0]?.id || '';
  }, [events]);
  const currentEvents = events.filter((e) => e.gameId === state?.gameId);
  const unsupported =
    state &&
    [state.blue, state.red].some((t) =>
      [t.kills, t.gold, t.towers, t.dragons, t.barons].includes(null),
    );
  const next = matches.find((m) => m.status === 'scheduled');
  return (
    <section className="panel expanded">
      <header className="panel-header">
        <span className="brand">
          <span className="brand-icon">L</span> LoL LIVE <span className="league">WORLDS</span>
        </span>
        <div className="header-actions">
          <button title="설정" aria-label="설정 열기" onClick={onSettings}>
            ⚙
          </button>
          <button title="접기" aria-label="접기" onClick={onCollapse}>
            ⌄
          </button>
        </div>
      </header>
      <div className="panel-body">
        <div className="match-caption">
          <span>
            {state?.status === 'ended'
              ? '경기 종료'
              : state
                ? `${state.gameNumber || '—'}세트 · ${formatTime(state.gameTimeSeconds)}`
                : '경기 대기'}
          </span>
          <span className={`connection ${state?.connection || 'offline'}`}>
            {replay ? '모의 데이터' : status}
          </span>
        </div>
        {state ? (
          <>
            <div className="match-heading">
              <strong>{state.blue.shortName}</strong>
              <span>
                {state.blue.seriesWins}
                <small>:</small>
                {state.red.seriesWins}
              </span>
              <strong>{state.red.shortName}</strong>
            </div>
            <div className="stat-table">
              <div className="stat-row stat-label">
                <span>{state.blue.shortName}</span>
                <span>현재 게임</span>
                <span>{state.red.shortName}</span>
              </div>
              {(
                [
                  ['킬', 'kills'],
                  ['골드', 'gold'],
                  ['타워', 'towers'],
                  ['드래곤', 'dragons'],
                  ['바론', 'barons'],
                ] as const
              ).map(([label, key]) => (
                <div className="stat-row" key={key}>
                  <strong>{stat(state.blue[key])}</strong>
                  <span>{label}</span>
                  <strong>{stat(state.red[key])}</strong>
                </div>
              ))}
            </div>
            {unsupported && <p className="unsupported">— 통계 미지원</p>}
          </>
        ) : (
          <div className="empty-panel">
            <span>◌</span>
            <p>진행 중 경기 없음</p>
            {next?.scheduledAt && (
              <small>다음 경기 {new Date(next.scheduledAt).toLocaleString('ko-KR')}</small>
            )}
            <button onClick={onSettings}>경기 선택</button>
          </div>
        )}
        <div className="log-heading">
          <span>경기 기록</span>
          <span>{currentEvents.length}건</span>
        </div>
        {newCount > 0 && (
          <button
            className="new-events"
            onClick={() => {
              scroller.current?.scrollTo({ top: 0 });
              setNewCount(0);
              atTop.current = true;
            }}
          >
            새 기록 {newCount}건 ↑
          </button>
        )}
        <div
          className="event-log"
          ref={scroller}
          onScroll={() => {
            atTop.current = (scroller.current?.scrollTop || 0) < 8;
            if (atTop.current) setNewCount(0);
          }}
        >
          {currentEvents.length ? (
            currentEvents.map((e) => (
              <article className={`log-row ${e.priority}`} key={e.id}>
                <time>{formatTime(e.gameTimeSeconds)}</time>
                <div>
                  <span className="event-type">{names[e.type]}</span>
                  <p>{e.messageKo}</p>
                </div>
              </article>
            ))
          ) : (
            <p className="log-empty">새로운 경기 기록을 기다리는 중</p>
          )}
          {hasMore && (
            <button className="load-more" onClick={onLoadMore}>
              이전 기록 불러오기
            </button>
          )}
        </div>
      </div>
      <footer className="panel-footer" title="방송보다 지연될 수 있음">
        {state
          ? `최근 데이터 수신 ${new Date(state.receivedAt).toLocaleTimeString('ko-KR', { hour12: false })}`
          : '데이터 수신 대기'}
        <span>방송 지연 가능</span>
      </footer>
    </section>
  );
}
