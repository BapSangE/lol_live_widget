import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react';
import { hasTeam } from '../lib/favorites';
import { showWidget } from '../lib/native';
import { useWidgetStore } from '../state/widgetStore';
import type { UserSettings } from '../types/contracts';

/** One announcement per series, including when a live favorite is discovered at startup. */
export function useFavoriteTeam(
  settings: UserSettings,
  enabled: boolean,
  setSettings: Dispatch<SetStateAction<UserSettings>>,
) {
  const matches = useWidgetStore((s) => s.matches);
  const sourceMode = useWidgetStore((s) => s.sourceMode);
  const announced = useRef(new Set(settings.notifiedFavoriteMatchIds));
  const scheduled = useRef(new Set<string>());
  const [alert, setAlert] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || sourceMode !== 'live' || !settings.favoriteTeam) return;
    for (const id of settings.notifiedFavoriteMatchIds) announced.current.add(id);
    for (const match of matches)
      if (match.status === 'scheduled') scheduled.current.add(match.matchId);
    const favorite = matches.find(
      (m) => m.status === 'live' && hasTeam(m, settings.favoriteTeam!.id),
    );
    if (!favorite || announced.current.has(favorite.matchId)) return;
    announced.current.add(favorite.matchId);
    setSettings((s) => ({
      ...s,
      preferredMatchId: favorite.matchId,
      notifiedFavoriteMatchIds: [
        ...s.notifiedFavoriteMatchIds.filter((id) => id !== favorite.matchId),
        favorite.matchId,
      ].slice(-50),
    }));
    setAlert(
      `${settings.favoriteTeam.name} 경기 ${scheduled.current.has(favorite.matchId) ? '시작' : '진행 중'} · ${favorite.blue.shortName} vs ${favorite.red.shortName}`,
    );
    useWidgetStore.getState().setMode('expanded');
    void showWidget().catch(() =>
      setAlert('응원 팀 경기를 선택했습니다. 메뉴에서 위젯을 열어 주세요.'),
    );
  }, [
    enabled,
    sourceMode,
    matches,
    settings.favoriteTeam,
    settings.notifiedFavoriteMatchIds,
    setSettings,
  ]);

  useEffect(() => {
    if (!alert) return;
    const timer = setTimeout(() => setAlert(null), 15_000);
    return () => clearTimeout(timer);
  }, [alert]);

  return { alert, dismiss: () => setAlert(null) };
}
