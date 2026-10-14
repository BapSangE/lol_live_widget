import type { components } from './api.generated';
export type MatchState = components['schemas']['MatchState'];
export type MatchEvent = components['schemas']['MatchEvent'];
export type EventType = MatchEvent['type'];
export type TeamState = components['schemas']['TeamState'];
export type MatchSummary = components['schemas']['MatchSummary'];
export type SyncSnapshot = components['schemas']['SyncSnapshot'];
export type EventsPage = components['schemas']['EventsPage'];
export interface UserSettings {
  schemaVersion: 1;
  opacityPercent: number;
  brightenOnHover: boolean;
  eventDisplaySeconds: number;
  preferredMatchId: string | null;
  importantTypes: EventType[];
  alwaysOnTop: boolean;
  launchAtLogin: boolean;
  theme: 'light' | 'dark' | 'system';
  widgetPosition: { monitorKey: string | null; x: number; y: number; anchor?: 'compact' } | null;
}
