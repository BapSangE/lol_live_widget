import { useEffect, useRef } from 'react';
import { useWidgetStore } from '../state/widgetStore';
import { demoEvents, demoFrames, demoMatch } from '../lib/demo';
import { parseSSE, wait } from '../lib/sse';
import type {
  MatchEvent,
  MatchState,
  MatchSummary,
  SyncSnapshot,
  UserSettings,
} from '../types/contracts';
export const serverURL = (import.meta.env.VITE_SERVER_URL as string | undefined)?.replace(
  /\/$/,
  '',
);
if (serverURL) {
  const u = new URL(serverURL);
  if (
    u.protocol !== 'https:' &&
    !(
      import.meta.env.DEV &&
      u.protocol === 'http:' &&
      ['127.0.0.1', 'localhost'].includes(u.hostname)
    )
  )
    throw new Error('Server must use HTTPS');
}
class HTTPError extends Error {
  constructor(public status: number) {
    super(`HTTP ${status}`);
  }
}
interface Health {
  sourceMode?: 'live' | 'replay';
  sourceStatus: string;
}
export function useMatchStream(settings: UserSettings, loaded: boolean) {
  const preferences = useRef(settings);
  preferences.current = settings;
  useEffect(() => {
    if (!loaded) return;
    const controller = new AbortController(),
      signal = controller.signal,
      store = useWidgetStore;
    const mode = store.getState().mode;
    store.getState().reset();
    store.getState().setMode(mode);
    if (!serverURL) {
      let index = 0;
      store.setState({ matches: [demoMatch], sourceMode: 'replay', connected: true });
      store.getState().setState({ ...demoFrames[0], receivedAt: new Date().toISOString() });
      const timer = setInterval(() => {
        index = Math.min(index + 1, demoFrames.length - 1);
        const frame = { ...demoFrames[index], receivedAt: new Date().toISOString() };
        store.getState().setState(frame);
        store.getState().addEvents(
          demoEvents.filter((e) => e.sourceRevision === frame.revision),
          true,
          preferences.current,
        );
        if (index === demoFrames.length - 1) {
          store.setState({ matches: [{ ...demoMatch, status: 'ended' }] });
          clearInterval(timer);
        }
      }, 10_000);
      return () => {
        controller.abort();
        clearInterval(timer);
      };
    }
    store.setState({ sourceMode: 'live' });
    let selected: string | null = null,
      session: AbortController | null = null,
      discovery: Promise<void> | null = null;
    const json = async <T>(path: string, requestSignal: AbortSignal = signal): Promise<T> => {
      const request = new AbortController();
      const abort = () => request.abort();
      requestSignal.addEventListener('abort', abort, { once: true });
      const timeout = setTimeout(() => request.abort(), 10_000);
      try {
        const r = await fetch(`${serverURL}/api/v1${path}`, { signal: request.signal });
        if (!r.ok) throw new HTTPError(r.status);
        return (await r.json()) as T;
      } finally {
        clearTimeout(timeout);
        requestSignal.removeEventListener('abort', abort);
      }
    };
    const startSession = (matchId: string) => {
      session?.abort();
      const active = new AbortController();
      session = active;
      const abort = () => active.abort();
      signal.addEventListener('abort', abort, { once: true });
      const current = () => !signal.aborted && !active.signal.aborted && selected === matchId;
      store.setState({
        state: null,
        events: [],
        ticker: null,
        tickerUntil: 0,
        nextCursor: null,
        historyExhausted: false,
        connected: false,
      });
      const run = async () => {
        let cursor = '',
          epoch = '',
          attempt = 0;
        while (current()) {
          try {
            const snap = await json<SyncSnapshot>(
              `/matches/${encodeURIComponent(matchId)}/sync`,
              active.signal,
            );
            if (!current()) return;
            const nextEpoch = snap.streamCursor.split(':')[0],
              restarted = Boolean(epoch && epoch !== nextEpoch);
            const changedGame = store.getState().state?.gameId !== snap.state.gameId;
            epoch = nextEpoch;
            store.setState({
              ...(restarted ? { events: [] } : {}),
              ...(restarted || changedGame ? { nextCursor: null, historyExhausted: false } : {}),
              ticker: null,
              tickerUntil: 0,
              state: snap.state,
              sourceMode: snap.sourceMode,
              notice: restarted ? '서버 재시작으로 로그가 초기화됨' : null,
            });
            store.getState().addEvents(snap.events, false, preferences.current);
            cursor = snap.streamCursor;
            const response = await fetch(
              `${serverURL}/api/v1/matches/${encodeURIComponent(matchId)}/stream`,
              { signal: active.signal, headers: { 'Last-Event-ID': cursor } },
            );
            if (!response.ok || !response.body) throw new HTTPError(response.status);
            if (!current()) return;
            store.setState({ connected: true });
            let resync = false;
            for await (const message of parseSSE(response.body, active.signal)) {
              if (!current()) return;
              if (message.event === 'resync_required') {
                resync = true;
                break;
              }
              if (message.event === 'state')
                store.getState().setState(JSON.parse(message.data) as MatchState);
              else if (message.event === 'match_event')
                store
                  .getState()
                  .addEvents([JSON.parse(message.data) as MatchEvent], true, preferences.current);
              if (message.id) cursor = message.id;
              attempt = 0;
            }
            if (resync) continue;
            throw new Error('Stream ended');
          } catch (error) {
            if (!current()) return;
            console.warn('Match connection unavailable', error);
            store.setState({ connected: false, notice: '재연결 중' });
            if (error instanceof HTTPError && error.status === 404) await refreshDiscovery();
            if (!current()) return;
            await wait([2, 4, 8, 16, 30][Math.min(attempt++, 4)] * 1000, active.signal).catch(
              () => {},
            );
            // REST-sync history before retry; only events newer than its cursor can alert.
          }
        }
      };
      void run()
        .catch((error) => {
          if (current()) console.error(error);
        })
        .finally(() => signal.removeEventListener('abort', abort));
    };
    const refreshDiscovery = (): Promise<void> => {
      if (discovery) return discovery;
      discovery = (async () => {
        try {
          const [matches, health] = await Promise.all([
            json<MatchSummary[]>('/matches?league=worlds'),
            json<Health>('/health'),
          ]);
          if (signal.aborted) return;
          const preferred = preferences.current.preferredMatchId;
          const explicit = matches.find((m) => m.matchId === preferred);
          const choice =
            explicit?.status === 'scheduled'
              ? null
              : explicit || matches.find((m) => m.status === 'live');
          const next = choice?.matchId || null;
          const notice =
            health.sourceStatus === 'access_denied'
              ? '데이터 접근 불가'
              : health.sourceStatus === 'rate_limited'
                ? '갱신 일시 지연'
                : health.sourceStatus === 'source_unavailable'
                  ? '데이터 공급원 연결 실패'
                  : null;
          store.setState({
            matches,
            sourceMode: health.sourceMode || (health.sourceStatus === 'replay' ? 'replay' : 'live'),
            ...(notice ? { notice } : {}),
          });
          if (next !== selected) {
            selected = next;
            session?.abort();
            if (next) startSession(next);
            else
              store.setState({
                state: null,
                events: [],
                ticker: null,
                tickerUntil: 0,
                connected: true,
                nextCursor: null,
                historyExhausted: false,
              });
          } else if (!next) store.setState({ connected: true });
        } catch (error) {
          if (!signal.aborted) {
            console.warn('Match discovery unavailable', error);
            if (!selected) store.setState({ connected: false, notice: '재연결 중' });
          }
        } finally {
          discovery = null;
        }
      })();
      return discovery;
    };
    void refreshDiscovery();
    const timer = setInterval(() => void refreshDiscovery(), 60_000);
    // Retry initial discovery faster than schedule refresh after a transport outage.
    let retryAttempt = 0;
    const recover = async () => {
      while (!signal.aborted) {
        await wait([2, 4, 8, 16, 30][Math.min(retryAttempt++, 4)] * 1000, signal).catch(() => {});
        if (signal.aborted) return;
        if (!store.getState().connected && !selected) await refreshDiscovery();
        else retryAttempt = 0;
      }
    };
    void recover();
    return () => {
      controller.abort();
      session?.abort();
      clearInterval(timer);
    };
  }, [loaded, settings.preferredMatchId]);
}
