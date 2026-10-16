import type { EventType, MatchSummary, UserSettings } from '../types/contracts';
const eventNames: Record<EventType, string> = {
  GAME_END: '게임 종료',
  BARON: '바론',
  ELDER: '장로 드래곤',
  GOLD_LEAD_CHANGE: '골드 역전',
  DRAGON_SOUL: '드래곤 영혼',
  MULTIKILL_WINDOW: '킬 교환',
  DRAGON: '드래곤',
  TOWER: '타워',
  KILL_DELTA: '일반 킬',
};
interface Props {
  settings: UserSettings;
  matches: MatchSummary[];
  onChange: (patch: Partial<UserSettings>) => void;
  onBack: () => void;
}
export function SettingsPanel({ settings, matches, onChange, onBack }: Props) {
  return (
    <section className="panel settings">
      <header className="panel-header">
        <span className="settings-title">설정</span>
        <button className="text-button" onClick={onBack}>
          완료
        </button>
      </header>
      <div className="settings-scroll">
        <label className="field">
          경기 선택
          <select
            value={settings.preferredMatchId || ''}
            onChange={(e) => onChange({ preferredMatchId: e.target.value || null })}
          >
            <option value="">진행 중 경기 자동 선택</option>
            {matches.map((m) => (
              <option key={m.matchId} value={m.matchId}>
                {m.blue.shortName} vs {m.red.shortName}
                {m.status === 'ended'
                  ? ' · 종료'
                  : m.status === 'scheduled'
                    ? ' · 예정'
                    : ''}
              </option>
            ))}
          </select>
        </label>
        <label className="field inline-field">
          글자 크기
          <select
            value={settings.fontScalePercent}
            onChange={(e) =>
              onChange({
                fontScalePercent: Number(
                  e.target.value,
                ) as UserSettings['fontScalePercent'],
              })
            }
          >
            <option value="100">기본 (100%)</option>
            <option value="120">크게 (120%)</option>
            <option value="140">아주 크게 (140%)</option>
          </select>
        </label>
        <div className="setting-group">
          <label htmlFor="opacity" className="range-label">
            전체 불투명도 <strong>{settings.opacityPercent}%</strong>
          </label>
          <input
            id="opacity"
            type="range"
            min="10"
            max="100"
            step="5"
            value={settings.opacityPercent}
            onChange={(e) => onChange({ opacityPercent: Number(e.target.value) })}
          />
          <p className="hint">배경·글자·아이콘·테두리에 함께 적용</p>
        </div>
        <label className="toggle-row">
          <span>호버 시 100% 불투명도</span>
          <input
            type="checkbox"
            checked={settings.brightenOnHover}
            onChange={(e) => onChange({ brightenOnHover: e.target.checked })}
          />
        </label>
        <label className="toggle-row">
          <span>항상 위</span>
          <input
            type="checkbox"
            checked={settings.alwaysOnTop}
            onChange={(e) => onChange({ alwaysOnTop: e.target.checked })}
          />
        </label>
        <label className="toggle-row">
          <span>로그인 시 자동 실행</span>
          <input
            type="checkbox"
            checked={settings.launchAtLogin}
            onChange={(e) => onChange({ launchAtLogin: e.target.checked })}
          />
        </label>
        <label className="field inline-field">
          이벤트 표시 시간
          <select
            value={settings.eventDisplaySeconds}
            onChange={(e) => onChange({ eventDisplaySeconds: Number(e.target.value) })}
          >
            {Array.from({ length: 13 }, (_, i) => i + 3).map((n) => (
              <option key={n} value={n}>
                {n}초
              </option>
            ))}
          </select>
        </label>
        <label className="field inline-field">
          테마
          <select
            value={settings.theme}
            onChange={(e) => onChange({ theme: e.target.value as UserSettings['theme'] })}
          >
            <option value="light">라이트</option>
            <option value="dark">다크</option>
            <option value="system">시스템</option>
          </select>
        </label>
        <fieldset className="event-filters">
          <legend>티커에 표시할 이벤트</legend>
          {(Object.keys(eventNames) as EventType[]).map((type) => (
            <label key={type}>
              <input
                type="checkbox"
                checked={settings.importantTypes.includes(type)}
                onChange={(e) =>
                  onChange({
                    importantTypes: e.target.checked
                      ? [...settings.importantTypes, type]
                      : settings.importantTypes.filter((t) => t !== type),
                  })
                }
              />
              {eventNames[type]}
            </label>
          ))}
        </fieldset>
        <p className="hint">
          알림은 무음이며, 선택하지 않은 이벤트도 경기 기록에 남습니다.
        </p>
      </div>
    </section>
  );
}
