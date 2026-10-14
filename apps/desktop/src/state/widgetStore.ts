import { create } from 'zustand';
import type { MatchEvent, MatchState, MatchSummary, UserSettings } from '../types/contracts';
import { chooseTicker } from '../lib/policies';
type Mode = 'compact' | 'expanded' | 'settings';
interface WidgetState {
  mode: Mode;
  state: MatchState | null;
  matches: MatchSummary[];
  events: MatchEvent[];
  ticker: MatchEvent | null;
  tickerUntil: number;
  sourceMode: 'live' | 'replay';
  playback: {
    kind: 'archive';
    elapsedSeconds: number;
    durationSeconds: number;
    finished: boolean;
  } | null;
  notice: string | null;
  connected: boolean;
  nextCursor: string | null;
  historyExhausted: boolean;
  reset(): void;
  setMode(mode: Mode): void;
  setState(state: MatchState): void;
  addEvents(events: MatchEvent[], notify: boolean, settings: UserSettings): void;
  expire(now: number): void;
}
const initial = {
  mode: 'compact' as Mode,
  state: null,
  matches: [],
  events: [],
  ticker: null,
  tickerUntil: 0,
  sourceMode: 'replay' as const,
  playback: null,
  notice: null,
  connected: false,
  nextCursor: null,
  historyExhausted: false,
};
export const useWidgetStore = create<WidgetState>((set, get) => ({
  ...initial,
  reset: () => set({ ...initial }),
  setMode: (mode) => set({ mode, ticker: null, tickerUntil: 0 }),
  setState: (state) => {
    const current = get().state;
    if (
      current &&
      current.matchId === state.matchId &&
      current.gameId === state.gameId &&
      state.revision < current.revision
    )
      return;
    const changed = current?.gameId !== state.gameId;
    set({
      state,
      ...(changed
        ? {
            ticker: null,
            tickerUntil: 0,
            nextCursor: null,
            historyExhausted: false,
          }
        : {}),
    });
  },
  addEvents: (incoming, notify, settings) => {
    const state = get(),
      known = new Set(state.events.map((e) => e.id));
    const fresh = incoming.filter((e) => {
      if (known.has(e.id)) return false;
      known.add(e.id);
      return true;
    });
    const events = [...fresh, ...state.events]
      .sort(
        (a, b) =>
          Date.parse(b.observedAt) - Date.parse(a.observedAt) ||
          (a.gameId === b.gameId ? b.sourceRevision - a.sourceRevision : 0),
      )
      .slice(0, 1000);
    const eligible = fresh.filter((e) => !state.state || e.gameId === state.state.gameId);
    const ticker =
      notify && state.mode === 'compact'
        ? chooseTicker(state.ticker, eligible, settings.importantTypes)
        : state.ticker;
    set({
      events,
      ticker,
      tickerUntil:
        ticker && ticker.id !== state.ticker?.id
          ? Date.now() + settings.eventDisplaySeconds * 1000
          : state.tickerUntil,
    });
  },
  expire: (now) => {
    if (get().ticker && now >= get().tickerUntil) set({ ticker: null, tickerUntil: 0 });
  },
}));
