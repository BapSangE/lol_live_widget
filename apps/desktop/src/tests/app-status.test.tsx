import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { defaults } from '../lib/policies';
import { useWidgetStore } from '../state/widgetStore';
import App from '../App';
import { demoEvents, demoFrames } from '../lib/demo';

vi.mock('../hooks/useSettings', () => ({
  useSettings: () => ({
    settings: defaults,
    setSettings: vi.fn(),
    loaded: true,
    error: null,
    setError: vi.fn(),
  }),
}));
vi.mock('../hooks/useMatchStream', () => ({
  serverURL: 'http://127.0.0.1:8000',
  useMatchStream: () => {},
}));

afterEach(() => {
  cleanup();
  useWidgetStore.getState().reset();
});

it('shows waiting instead of disconnected when discovery succeeds without a live match', () => {
  useWidgetStore.setState({
    mode: 'expanded',
    connected: true,
    sourceMode: 'live',
  });
  render(<App />);
  expect(screen.getByText('진행 중 경기 없음')).toBeVisible();
  expect(screen.getAllByText('경기 대기')).toHaveLength(2);
  expect(screen.queryByText('연결 끊김')).not.toBeInTheDocument();
});

it('keeps the latest current-game record below the compact score and opens full history', () => {
  const state = demoFrames[0];
  const current = {
    ...demoEvents[0],
    matchId: state.matchId,
    gameId: state.gameId!,
    messageKo: 'GEN 킬 기록',
    gameTimeSeconds: 123,
  };
  useWidgetStore.setState({
    connected: true,
    sourceMode: 'live',
    state,
    events: [{ ...current, id: 'old-game', gameId: 'previous', messageKo: '이전 세트 기록' }, current],
  });
  render(<App />);
  expect(screen.getByText('2 : 1')).toBeVisible();
  expect(screen.getByText('GEN 킬 기록')).toBeVisible();
  expect(screen.getByText('02:03')).toBeVisible();
  expect(screen.queryByText('이전 세트 기록')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '최근 경기 기록 열기' }));
  expect(useWidgetStore.getState().mode).toBe('expanded');
});
