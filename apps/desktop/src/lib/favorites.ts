import type { FavoriteTeam, MatchSummary } from '../types/contracts';
export const hasTeam = (match: MatchSummary, teamId: string) =>
  match.blue?.id === teamId || match.red?.id === teamId;

export function favoriteTeams(matches: MatchSummary[], saved: FavoriteTeam | null) {
  const teams = new Map<string, FavoriteTeam>();
  if (saved) teams.set(saved.id, saved);
  for (const match of matches)
    for (const team of [match.blue, match.red])
      if (team?.id && team.name && !/^(tbd|unknown)$/i.test(team.shortName))
        teams.set(team.id, { id: team.id, name: team.name });
  return [...teams.values()].sort((a, b) => a.name.localeCompare(b.name));
}

export function nextFavoriteMatch(matches: MatchSummary[], teamId: string) {
  return matches
    .filter((m) => m.status === 'scheduled' && hasTeam(m, teamId))
    .sort(
      (a, b) =>
        (Date.parse(a.scheduledAt || '') || Infinity) -
        (Date.parse(b.scheduledAt || '') || Infinity),
    )[0];
}
