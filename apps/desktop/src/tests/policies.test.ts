import { describe, it, expect } from 'vitest';
import {
  chooseTicker,
  deriveConnection,
  effectiveOpacity,
  geometry,
  validateSettings,
} from '../lib/policies';
import type { MatchEvent } from '../types/contracts';
const ev = (type: MatchEvent['type'], id = type): MatchEvent => ({
  id,
  matchId: 'm',
  gameId: 'g',
  type,
  gameTimeSeconds: 10,
  occurredAt: null,
  observedAt: '2026-10-14T00:00:00Z',
  teamId: 't',
  priority: 'important',
  messageKo: '이벤트',
  confidence: 'derived',
  sourceRevision: 2,
});
describe('ticker', () => {
  it('selects strongest and never promotes equal/lower priority', () => {
    expect(chooseTicker(null, [ev('TOWER'), ev('BARON')], ['TOWER', 'BARON'])?.type).toBe('BARON');
    expect(chooseTicker(ev('BARON'), [ev('TOWER')], ['TOWER', 'BARON'])?.type).toBe('BARON');
    expect(chooseTicker(ev('BARON'), [ev('GAME_END')], ['GAME_END'])?.type).toBe('GAME_END');
    expect(chooseTicker(null, [ev('KILL_DELTA')], ['BARON'])).toBeNull();
  });
  it('uses received frame age, with exact threshold boundaries', () => {
    expect(deriveConnection(30)).toBe('live');
    expect(deriveConnection(31)).toBe('delayed');
    expect(deriveConnection(120)).toBe('delayed');
    expect(deriveConnection(121)).toBe('offline');
  });
  it('does not brighten unless enabled', () => {
    expect(effectiveOpacity(65, false, true)).toBe(65);
    expect(effectiveOpacity(35, true, true)).toBe(100);
    expect(effectiveOpacity(35, true, false)).toBe(35);
  });
  it('expands upward at bottom and clamps negative-origin monitor', () => {
    expect(geometry({ x: 200, y: 950 }, true, { x: 0, y: 0, width: 1920, height: 1040 }).y).toBe(
      612,
    );
    const r = geometry({ x: -5, y: 20 }, true, { x: -1280, y: 0, width: 1280, height: 984 });
    expect(r.x).toBe(-350);
    expect(r.y).toBe(20);
  });
  it('keeps both compact rows inside the monitor and preserves the bottom edge on expansion', () => {
    const area = { x: 0, y: 0, width: 1920, height: 1040 };
    const compact = geometry({ x: 1800, y: 1000 }, false, area);
    expect(compact).toEqual({ x: 1570, y: 978, width: 350, height: 62 });
    const expanded = geometry({ x: compact.x, y: compact.y }, true, area);
    expect(expanded.width).toBe(compact.width);
    expect(expanded.y + expanded.height).toBe(1040);
    const small = geometry({ x: 20, y: 20 }, false, { x: 0, y: 0, width: 200, height: 50 });
    expect(small).toEqual({ x: 0, y: 0, width: 200, height: 50 });
  });
  it('restores corrupted settings safely', () => {
    const s = validateSettings({
      opacityPercent: 3,
      launchAtLogin: 'yes',
      eventDisplaySeconds: 99,
    });
    expect(s.opacityPercent).toBe(65);
    expect(s.launchAtLogin).toBe(false);
    expect(s.eventDisplaySeconds).toBe(6);
  });
});
it('does not reinterpret an unknown settings version as v1', () => {
  expect(
    validateSettings({ schemaVersion: 2, opacityPercent: 35, launchAtLogin: true }).opacityPercent,
  ).toBe(65);
});
