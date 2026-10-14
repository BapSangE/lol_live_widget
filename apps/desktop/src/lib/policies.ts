import type { EventType, MatchEvent, UserSettings } from '../types/contracts';
export const eventRank: Record<EventType, number> = {
  GAME_END: 5,
  BARON: 4,
  ELDER: 4,
  GOLD_LEAD_CHANGE: 4,
  DRAGON_SOUL: 3,
  MULTIKILL_WINDOW: 3,
  DRAGON: 2,
  TOWER: 2,
  KILL_DELTA: 1,
};
export const defaultImportant: EventType[] = [
  'GAME_END',
  'BARON',
  'ELDER',
  'GOLD_LEAD_CHANGE',
  'DRAGON_SOUL',
  'MULTIKILL_WINDOW',
  'DRAGON',
  'TOWER',
];
export const defaults: UserSettings = {
  schemaVersion: 1,
  opacityPercent: 65,
  brightenOnHover: false,
  eventDisplaySeconds: 6,
  preferredMatchId: null,
  importantTypes: defaultImportant,
  alwaysOnTop: true,
  launchAtLogin: false,
  theme: 'light',
  widgetPosition: null,
};
export function chooseTicker(
  current: MatchEvent | null,
  events: MatchEvent[],
  enabled: EventType[],
): MatchEvent | null {
  let selected = current;
  for (const event of events) {
    if (
      enabled.includes(event.type) &&
      (!selected || eventRank[event.type] > eventRank[selected.type])
    )
      selected = event;
  }
  return selected;
}
export const deriveConnection = (seconds: number): 'live' | 'delayed' | 'offline' =>
  seconds > 120 ? 'offline' : seconds > 30 ? 'delayed' : 'live';
export const effectiveOpacity = (percent: number, enabled: boolean, hovered: boolean) =>
  enabled && hovered ? 100 : percent;
export interface Area {
  x: number;
  y: number;
  width: number;
  height: number;
}
export function geometry(anchor: { x: number; y: number }, expanded: boolean, area: Area) {
  const width = Math.min(expanded ? 350 : 270, area.width),
    height = Math.min(expanded ? 300 : 38, area.height);
  const upward = anchor.y + 38 >= area.y + area.height * 0.6;
  const y = expanded && upward ? anchor.y + 38 - height : anchor.y;
  return {
    x: Math.max(area.x, Math.min(anchor.x, area.x + area.width - width)),
    y: Math.max(area.y, Math.min(y, area.y + area.height - height)),
    width,
    height,
  };
}
export function validateSettings(raw: unknown): UserSettings {
  if (!raw || typeof raw !== 'object') return { ...defaults };
  const v = raw as Record<string, unknown>;
  if (v.schemaVersion !== undefined && v.schemaVersion !== 1) return { ...defaults };
  const bool = (k: string, d: boolean) => (typeof v[k] === 'boolean' ? (v[k] as boolean) : d);
  const num = (k: string, min: number, max: number, step: number, d: number) =>
    typeof v[k] === 'number' &&
    Number.isFinite(v[k]) &&
    v[k] >= min &&
    v[k] <= max &&
    v[k] % step === 0
      ? (v[k] as number)
      : d;
  const p = v.widgetPosition as Record<string, unknown> | null;
  return {
    schemaVersion: 1,
    opacityPercent: num('opacityPercent', 10, 100, 5, 65),
    brightenOnHover: bool('brightenOnHover', false),
    eventDisplaySeconds: num('eventDisplaySeconds', 3, 15, 1, 6),
    preferredMatchId: typeof v.preferredMatchId === 'string' ? v.preferredMatchId : null,
    importantTypes: Array.isArray(v.importantTypes)
      ? v.importantTypes.filter((t): t is EventType => typeof t === 'string' && t in eventRank)
      : [...defaultImportant],
    alwaysOnTop: bool('alwaysOnTop', true),
    launchAtLogin: bool('launchAtLogin', false),
    theme: ['light', 'dark', 'system'].includes(v.theme as string)
      ? (v.theme as UserSettings['theme'])
      : 'light',
    widgetPosition:
      p &&
      typeof p.x === 'number' &&
      Number.isFinite(p.x) &&
      typeof p.y === 'number' &&
      Number.isFinite(p.y)
        ? {
            monitorKey: typeof p.monitorKey === 'string' ? p.monitorKey : null,
            x: p.x,
            y: p.y,
            anchor: 'compact',
          }
        : null,
  };
}
export const formatTime = (seconds: number | null) =>
  seconds === null
    ? '--:--'
    : `${Math.floor(seconds / 60)
        .toString()
        .padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
export const stat = (value: number | null | undefined) =>
  value == null ? '—' : value.toLocaleString('ko-KR');
