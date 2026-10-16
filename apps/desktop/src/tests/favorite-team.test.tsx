import { afterEach, expect, it, vi } from 'vitest';
import {
  act,
  cleanup,
  fireEvent,
  render,
  renderHook,
  screen,
  waitFor,
} from '@testing-library/react';
import { useState } from 'react';
import { useFavoriteTeam } from '../hooks/useFavoriteTeam';
import { useWidgetStore } from '../state/widgetStore';
import { defaults, validateSettings } from '../lib/policies';
import { demoMatch } from '../lib/demo';
import { SettingsPanel } from '../components/SettingsPanel';
import { useSettings } from '../hooks/useSettings';
import { showWidget } from '../lib/native';
import type { MatchSummary, UserSettings } from '../types/contracts';
vi.mock('../lib/native', async (original) => ({
  ...(await original<typeof import('../lib/native')>()),
  showWidget: vi.fn().mockResolvedValue(undefined),
}));
const favorite = { id: demoMatch.blue.id, name: demoMatch.blue.name };
const match: MatchSummary = {
  ...demoMatch,
  matchId: 'favorite-series',
  status: 'scheduled',
  scheduledAt: '2030-01-01T10:00:00Z',
};
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.clearAllMocks();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  useWidgetStore.getState().reset();
});

it('switches to a newly live favorite series and alerts once across set changes and reopening', async () => {
  useWidgetStore.setState({ matches: [match], sourceMode: 'live' });
  const saved: UserSettings = {
    ...defaults,
    favoriteTeam: favorite,
    preferredMatchId: 'other',
  };
  const view = renderHook(() => {
    const [settings, setSettings] = useState<UserSettings>(saved);
    return { ...useFavoriteTeam(settings, true, setSettings), settings };
  });
  expect(view.result.current.alert).toBeNull();
  await act(async () =>
    useWidgetStore.setState({ matches: [{ ...match, status: 'live' }] }),
  );
  expect(view.result.current.settings.preferredMatchId).toBe(match.matchId);
  expect(view.result.current.alert).toContain('경기 시작');
  expect(useWidgetStore.getState().mode).toBe('expanded');
  expect(showWidget).toHaveBeenCalledTimes(1);
  const persisted = view.result.current.settings;
  expect(persisted.notifiedFavoriteMatchIds).toContain(match.matchId);
  await act(async () =>
    useWidgetStore.setState({
      matches: [{ ...match, status: 'live', gameId: 'next-game' }],
    }),
  );
  expect(showWidget).toHaveBeenCalledTimes(1);
  view.unmount();
  const reopened = renderHook(() => {
    const [s, set] = useState<UserSettings>(persisted);
    return useFavoriteTeam(s, true, set);
  });
  expect(reopened.result.current.alert).toBeNull();
  expect(showWidget).toHaveBeenCalledTimes(1);
});

it('never alerts for replay or an unrelated team, and handles an already live favorite on startup', async () => {
  const settings = { ...defaults, favoriteTeam: favorite };
  useWidgetStore.setState({
    matches: [{ ...match, status: 'live' }],
    sourceMode: 'replay',
  });
  const view = renderHook(() => {
    const [s, set] = useState<UserSettings>(settings);
    return useFavoriteTeam(s, true, set);
  });
  expect(showWidget).not.toHaveBeenCalled();
  await act(async () => useWidgetStore.setState({ sourceMode: 'live' }));
  expect(view.result.current.alert).toContain('경기 진행 중');
  view.unmount();
  vi.clearAllMocks();
  const unrelated = {
    ...settings,
    favoriteTeam: { id: 'not-in-this-match', name: 'Other' },
  };
  renderHook(() => {
    const [s, set] = useState<UserSettings>(unrelated);
    return useFavoriteTeam(s, true, set);
  });
  expect(showWidget).not.toHaveBeenCalled();
});

it('stores a selected favorite team and retains it when the schedule no longer lists it', async () => {
  function Settings({ matches }: { matches: MatchSummary[] }) {
    const { settings, setSettings, loaded } = useSettings();
    if (!loaded) return null;
    return (
      <SettingsPanel
        settings={settings}
        matches={matches}
        onChange={(p) => setSettings((s) => ({ ...s, ...p }))}
        onBack={() => {}}
      />
    );
  }
  const view = render(<Settings matches={[match]} />);
  const select = await screen.findByRole('combobox', { name: '응원 팀' });
  fireEvent.change(select, { target: { value: favorite.id } });
  expect(screen.getByText(/다음 경기/)).toBeInTheDocument();
  await waitFor(() =>
    expect(
      JSON.parse(localStorage.getItem('lol-widget-settings') || '{}').favoriteTeam,
    ).toEqual(favorite),
  );
  view.unmount();
  render(<Settings matches={[]} />);
  expect(await screen.findByRole('combobox', { name: '응원 팀' })).toHaveValue(
    favorite.id,
  );
  expect(screen.getByText('예정된 응원 팀 경기가 없습니다.')).toBeInTheDocument();
});

it('migrates older settings and rejects invalid favorite identifiers and notification history', () => {
  expect(validateSettings({ opacityPercent: 35 }).favoriteTeam).toBeNull();
  expect(
    validateSettings({ favoriteTeam: { id: '', name: 'Team' } }).favoriteTeam,
  ).toBeNull();
  expect(
    validateSettings({ ...defaults, favoriteTeam: favorite }).favoriteTeam,
  ).toEqual(favorite);
  expect(
    validateSettings({ ...defaults, notifiedFavoriteMatchIds: ['a', null, 10] })
      .notifiedFavoriteMatchIds,
  ).toEqual(['a']);
});

it('reconnects the real match stream to the favorite and permits later manual match selection', async () => {
  vi.useFakeTimers();
  vi.stubEnv('VITE_SERVER_URL', 'http://127.0.0.1:8000');
  vi.stubEnv('VITE_LEAGUE', 'worlds');
  const { useMatchStream } = await import('../hooks/useMatchStream');
  let live = false;
  const other = {
    ...match,
    matchId: 'other',
    status: 'live',
    blue: { ...match.blue, id: 'unrelated-a' },
    red: { ...match.red, id: 'unrelated-b' },
  };
  vi.stubGlobal('fetch', async (url: string) => {
    if (url.endsWith('/health'))
      return new Response(
        JSON.stringify({ sourceMode: 'live', sourceStatus: 'healthy' }),
      );
    if (url.includes('/matches?'))
      return new Response(
        JSON.stringify([other, { ...match, status: live ? 'live' : 'scheduled' }]),
      );
    if (url.endsWith('/sync'))
      return new Response(
        JSON.stringify({
          state: {
            ...demoMatch,
            ...(await import('../lib/demo')).demoFrames[0],
            matchId: url.includes('/other/') ? 'other' : match.matchId,
          },
          events: [],
          streamCursor: 'epoch:1',
          sourceMode: 'live',
        }),
      );
    return new Response(
      new ReadableStream({
        start(c) {
          c.enqueue(new TextEncoder().encode(': keepalive\n\n'));
        },
      }),
    );
  });
  const view = renderHook(() => {
    const [settings, setSettings] = useState<UserSettings>({
      ...defaults,
      favoriteTeam: favorite,
    });
    useMatchStream(settings, true);
    const result = useFavoriteTeam(settings, true, setSettings);
    return { ...result, settings, setSettings };
  });
  await act(async () => {
    for (let i = 0; i < 50; i++) await Promise.resolve();
  });
  expect(useWidgetStore.getState().state?.matchId).toBe('other');
  live = true;
  await act(async () => {
    await vi.advanceTimersByTimeAsync(60_000);
    for (let i = 0; i < 50; i++) await Promise.resolve();
  });
  expect(useWidgetStore.getState().state?.matchId).toBe(match.matchId);
  expect(showWidget).toHaveBeenCalledTimes(1);
  expect(view.result.current.alert).toContain('경기 시작');
  await act(async () => {
    view.result.current.setSettings((s) => ({
      ...s,
      preferredMatchId: 'other',
    }));
    for (let i = 0; i < 50; i++) await Promise.resolve();
  });
  expect(useWidgetStore.getState().state?.matchId).toBe('other');
  expect(showWidget).toHaveBeenCalledTimes(1);
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});
