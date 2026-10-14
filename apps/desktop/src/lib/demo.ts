import raw from '../../../../fixtures/raw_frames/demo.json';
import expected from '../../../../fixtures/expected_events/demo.json';
import type { MatchState, MatchEvent, MatchSummary } from '../types/contracts';
export const demoFrames = raw.map((f, i) => ({
  ...f,
  connection: 'live',
  receivedAt: new Date().toISOString(),
  revision: i + 1,
  sourceError: null,
})) as MatchState[];
export const demoEvents = expected as MatchEvent[];
export const demoMatch: MatchSummary = {
  matchId: 'demo-worlds',
  league: 'worlds',
  status: 'live',
  blue: demoFrames[0].blue,
  red: demoFrames[0].red,
  gameId: demoFrames[0].gameId,
  gameNumber: 4,
  scheduledAt: null,
};
