# API 계약

정본: Pydantic 모델, `openapi.json`. Desktop 타입은 OpenAPI에서 생성합니다. JSON camelCase, 시각 UTC ISO 8601, 게임 시간은 별도 초 단위.

- `GET /api/v1/health`: 상태, 공급원 상태, 최근 수집 시간, 공급원 지표.
- `GET /api/v1/matches?league=worlds&status=live`: 경기 목록. status 생략 시 예정/종료 포함.
- `GET /api/v1/matches/{id}/state`: 현재 상태. 없으면 404.
- `GET /api/v1/matches/{id}/events?limit=50&before=<event-id>`: 최신순 로그와 nextCursor. 최대 100. 만료 커서 410.
- `GET /api/v1/matches/{id}/sync`: 원자적 `{state,events,streamCursor,sourceMode}`. 최신 50개 사건.
- `GET /api/v1/matches/{id}/stream`: SSE, `Last-Event-ID` 지원.

SSE 전송 ID `epoch:sequence`와 사건 `MatchEvent.id`는 다릅니다. state revision은 게임별 증가하며 연결 상태 변경에는 동일 revision 재전송을 허용합니다. 게임별 revision 비교에서 gameId를 포함해야 합니다.

이력 커서 만료·epoch 변경은 `resync_required` 이벤트 후 연결 종료. 클라이언트는 /sync로 다시 동기화합니다. heartbeat 15초. 경기별 전송/사건 보관 각 1,000개. 종료 경기 24시간 후 제거.

DRAGON_SOUL을 계약에 추가했고 일반 킬 이름은 KILL_DELTA로 통일했습니다. sourceError는 접근 거절/429/공급원 실패를 정확히 표시하는 선택적 필드입니다. 재생 모드 sourceMode는 반드시 UI에 표시합니다.

파생 사건의 occurredAt은 null입니다. sourceTimestamp는 관측 시각이므로 실제 사건 발생 시각으로 단정하지 않습니다. sourceRevision과 observedAt으로 관측 근거를 추적합니다.

## 선수별 킬·사망 (v0.2.2)

`PLAYER_KILL`과 `PLAYER_DEATH`는 선수별 누적 K/D 변화에서 파생한 기록입니다. `messageKo`는 공급원의 선수 이름과 변화량을 표시합니다(예: `T1 Faker 킬 +1`). 상대 선수와의 처치 연결은 제공하지 않습니다. `confidence=derived`, `occurredAt=null`을 유지합니다. 선수 정보가 불완전하면 팀 합계 `KILL_DELTA`를 유지하고, 선수 변화량 합계가 팀 킬 변화량을 모두 설명하면 중복 팀 기록을 생략합니다.

## 추정 경과 시간

`MatchState`와 `MatchEvent`의 선택적 `estimatedGameTimeSeconds`는 세트의 첫 피드 프레임과 현재 데이터 프레임 사이의 벽시계 차이입니다. 공식 게임 시계인 `gameTimeSeconds`와 별개이며, 해당 값이 있으면 공식 값을 우선 표시합니다. UI에는 반드시 `추정`을 붙입니다. 경기 전 대기·일시정지는 빼지 않으므로 실제 게임 시계와 차이가 날 수 있습니다. 기준점을 얻지 못하면 null로 두고 통계 수집은 계속하며, 403·429 제한은 그대로 준수합니다.
