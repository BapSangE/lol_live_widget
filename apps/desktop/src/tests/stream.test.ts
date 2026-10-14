import { it, expect } from 'vitest';
import { parseSSE } from '../lib/sse';
import { useWidgetStore } from '../state/widgetStore';
import { defaults } from '../lib/policies';
import type { MatchEvent } from '../types/contracts';
it('parses chunked UTF-8 multiline SSE and ignores heartbeats', async () => {
  const text =
    ': keepalive\r\n\r\nevent: match_event\r\nid: e:2\r\ndata: {"messageKo":\r\ndata: "바론"}\r\n\r\n';
  const bytes = new TextEncoder().encode(text);
  const stream = new ReadableStream<Uint8Array>({
    start(c) {
      for (let i = 0; i < bytes.length; i += 3) c.enqueue(bytes.slice(i, i + 3));
      c.close();
    },
  });
  const result = [];
  for await (const m of parseSSE(stream)) result.push(m);
  expect(result).toEqual([{ event: 'match_event', id: 'e:2', data: '{"messageKo":\n"바론"}' }]);
});
it('does not alert historical events, clears ticker on expansion and deduplicates', () => {
  useWidgetStore.getState().reset();
  const event: MatchEvent = {
    id: 'a',
    matchId: 'm',
    gameId: 'g',
    type: 'BARON',
    gameTimeSeconds: 0,
    occurredAt: null,
    observedAt: new Date().toISOString(),
    teamId: null,
    priority: 'important',
    messageKo: '바론',
    confidence: 'derived',
    sourceRevision: 1,
  };
  useWidgetStore.getState().addEvents([event], false, defaults);
  expect(useWidgetStore.getState().ticker).toBeNull();
  useWidgetStore.getState().addEvents([{ ...event, id: 'b' }], true, defaults);
  expect(useWidgetStore.getState().ticker?.id).toBe('b');
  useWidgetStore.getState().setMode('expanded');
  expect(useWidgetStore.getState().ticker).toBeNull();
  useWidgetStore.getState().addEvents([event], true, defaults);
  expect(useWidgetStore.getState().events).toHaveLength(2);
});
it('retains a new game event even with 1000 prior-game events', () => {
  useWidgetStore.getState().reset();
  const base: MatchEvent = {
    id: 'old',
    matchId: 'm',
    gameId: 'old-game',
    type: 'KILL_DELTA',
    gameTimeSeconds: 0,
    occurredAt: null,
    observedAt: '2026-10-14T00:00:00Z',
    teamId: null,
    priority: 'normal',
    messageKo: '킬',
    confidence: 'derived',
    sourceRevision: 1000,
  };
  useWidgetStore.getState().addEvents(
    Array.from({ length: 1000 }, (_, i) => ({ ...base, id: `old-${i}`, sourceRevision: i + 1 })),
    false,
    defaults,
  );
  useWidgetStore
    .getState()
    .addEvents(
      [
        {
          ...base,
          id: 'new',
          gameId: 'new-game',
          sourceRevision: 1,
          observedAt: '2026-10-14T01:00:00Z',
        },
      ],
      false,
      defaults,
    );
  expect(useWidgetStore.getState().events[0].id).toBe('new');
  expect(useWidgetStore.getState().events).toHaveLength(1000);
});
