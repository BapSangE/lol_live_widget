import { afterEach, it, expect, vi } from 'vitest';
import { act, cleanup, renderHook } from '@testing-library/react';
import { useWidgetStore } from '../state/widgetStore';
import { defaults } from '../lib/policies';
import { demoFrames } from '../lib/demo';
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  useWidgetStore.getState().reset();
});
it('refreshes automatic match discovery while a stream remains open', async () => {
  vi.useFakeTimers();
  vi.stubEnv('VITE_SERVER_URL', 'http://127.0.0.1:8000');
  const { useMatchStream } = await import('../hooks/useMatchStream');
  let lists = 0;
  vi.stubGlobal('fetch', async (url: string) => {
    if (url.endsWith('/health'))
      return new Response(JSON.stringify({ sourceMode: 'replay', sourceStatus: 'replay' }));
    if (url.includes('/matches?')) {
      lists++;
      return new Response(
        JSON.stringify([{ matchId: lists === 1 ? 'a' : 'b', status: 'live', league: 'worlds' }]),
      );
    }
    if (url.endsWith('/sync'))
      return new Response(
        JSON.stringify({
          state: { ...demoFrames[0], matchId: url.includes('/a/') ? 'a' : 'b' },
          events: [],
          streamCursor: 'epoch:1',
          sourceMode: 'replay',
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
  renderHook(() => useMatchStream(defaults, true));
  await act(async () => {
    for (let i = 0; i < 30; i++) await Promise.resolve();
  });
  expect(useWidgetStore.getState().state?.matchId).toBe('a');
  await act(async () => {
    await vi.advanceTimersByTimeAsync(60_000);
    for (let i = 0; i < 30; i++) await Promise.resolve();
  });
  expect(useWidgetStore.getState().state?.matchId).toBe('b');
  expect(lists).toBeGreaterThan(1);
});
it('clears an old event pagination cursor on server epoch replacement', async () => {
  vi.useFakeTimers();
  vi.stubEnv('VITE_SERVER_URL', 'http://127.0.0.1:8000');
  const { useMatchStream } = await import('../hooks/useMatchStream');
  let syncs = 0,
    streams = 0;
  vi.stubGlobal('fetch', async (url: string) => {
    if (url.endsWith('/health'))
      return new Response(JSON.stringify({ sourceMode: 'replay', sourceStatus: 'replay' }));
    if (url.includes('/matches?'))
      return new Response(JSON.stringify([{ matchId: 'a', status: 'live', league: 'worlds' }]));
    if (url.endsWith('/sync')) {
      syncs++;
      return new Response(
        JSON.stringify({
          state: { ...demoFrames[0], matchId: 'a' },
          events: [],
          streamCursor: syncs === 1 ? 'old:1' : 'new:1',
          sourceMode: 'replay',
        }),
      );
    }
    streams++;
    return new Response(
      new ReadableStream({
        start(c) {
          if (streams === 1) c.close();
          else c.enqueue(new TextEncoder().encode(': keepalive\n\n'));
        },
      }),
    );
  });
  renderHook(() => useMatchStream(defaults, true));
  await act(async () => {
    for (let i = 0; i < 30; i++) await Promise.resolve();
  });
  useWidgetStore.setState({ nextCursor: 'old-event-id' });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(2000);
    for (let i = 0; i < 30; i++) await Promise.resolve();
  });
  expect(syncs).toBe(2);
  expect(useWidgetStore.getState().nextCursor).toBeNull();
});
