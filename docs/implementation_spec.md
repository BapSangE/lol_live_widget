# LoL Live Widget — Windows 실시간 문자 중계 구현 명세서

- 문서 버전: 1.0
- 작성 기준일: 2026-10-14
- 문서 상태: MVP 개발 기준선
- 2026-10-16 UI 보완: 최소화는 350×62(스코어바+최신 기록 한 줄), 확장은 350×400으로 변경해 폭을 일치시킨다. 설정은 350×300을 유지한다. 기록은 현재 세트의 최신 1건을 다음 기록까지 유지하며 기록 줄 클릭으로 상세를 펼친다. 확장 기록 영역은 최소 120px로 일반적인 기록 두 건을 함께 표시한다. 아래 본문의 270×38·350×300은 변경 전 규격이며 전체 창 크기·하단 앵커 계산에는 이 보완 규격을 우선 적용한다.
- 대상: Windows 10/11, 일반 사용자, 개발팀 및 AI 코딩 에이전트
- 목적: 설치 후 로그인 없이 이용하는 작은 플로팅 위젯으로 LoL e스포츠 실시간 스코어와 주요 이벤트 확인

## 0. 핵심 결정 사항 및 용어

| 항목 | 결정 |
|---|---|
| 클라이언트 | Windows용 Tauri 2 + React + TypeScript + Vite |
| 서버 | Python FastAPI, 단일 중앙 데이터 수집기 |
| 기본 위젯 | 270 × 38 논리 px, 드래그 이동 가능, 하단 근처 초기 배치 |
| 확장 위젯 | 350 × 300 논리 px (작업 영역에 따라 클램프) |
| 표시 | 기본 팀명·시리즈 세트 스코어·경기 시간; 이벤트 발생 시 동일 높이 한 줄 치환 |
| 상세 | 클릭 시 킬/골드/타워/오브젝트/문자 로그 |
| 기본 투명도 | 불투명도 65%, 10~100% / 5% 단위 슬라이더 |
| 투명도 범위 | **배경·문자·아이콘·테두리를 포함한 위젯 전체**. 부분 분리 금지 |
| 호버 자동 불투명 | 설정 제공, 기본 OFF. ON이면 호버 중 100%, 해제 시 복원 |
| 이벤트 발생 투명도 | **사용자 설정 유지**. 강제 증가 없음 |
| 기본 알림 | 무음. 전면 자동 확장 없음. 중요 이벤트만 6초 표시 |
| 실시간 수집 목표 | 서버에서 10초 주기 폴링(공급원 허용 범위에서 조절) |
| 배포 | Windows 설치 프로그램, 트레이 메뉴, 수동 업데이트 우선 |
| 로그인/계정 | MVP에 없음 |
| 경기 범위 | LoL Worlds 우선, 리그 확장 가능한 도메인 모델 |

**중요 구분**: UI의 '불투명도 65%'는 시각적으로 65%만 남는다는 뜻이다. 개발자 내부에서는 `opacity = 0.65`. '투명도 65%'라고 표시하지 않는다.

## 1. 목표와 범위

### 1.1 사용자 목표

1. 업무용 프로그램을 사용하면서 하단 스코어바에서 경기를 조용히 확인한다.
2. 킬 교환·드래곤·바론·골드 우위 변화 같은 주요 사건을 별도 영상 없이 알 수 있다.
3. 위젯을 드래그하고, 클릭하면 위로/아래로 확장해 기록을 본다.
4. 전체 위젯 불투명도를 슬라이더로 조절한다.
5. 연결 오류 시 가짜 실시간 상태를 표시하지 않는다.

### 1.2 비목표

- 영상/음성 중계, 화면 녹화, 업무 도구·파일·프로세스 이름 사칭
- 실제 Windows 작업표시줄 내부 삽입
- 시스템 입력 감시, 자동 창 숨김/다른 사람 접근 감지
- LLM 생성 해설, 자동 솔로킬/갱킹/한타/바론 스틸 단정
- 회원가입, 클라우드 개인화, 모바일 지원, 예측/베팅

## 2. IA 및 상태 머신

### 2.1 화면 목록

- `COMPACT`: 스코어바. 초기 폭 270, 높이 38.
- `EVENT`: 중요 이벤트 발생 후 6초간 스코어 영역을 문구로 교체. **크기 불변**.
- `EXPANDED`: 스코어, 세부 통계, 역순 이벤트 로그, 데이터 신선도.
- `SETTINGS`: 경기 선택, 불투명도 슬라이더, 호버 옵션, 이벤트 종류, 최상단, 알림 시간, 시작 동작.
- `EMPTY`: 경기 없음. '진행 중 경기 없음' + 다음 일정 가능 시 노출.
- `STALE`: 마지막 수집 시간이 허용 범위를 넘어선 상태.
- `ERROR`: 데이터 부재/인증 거부/접속 실패. 마지막 유효 상태와 오류 배너.

`COMPACT -> EXPANDED`: 스코어 영역 클릭. `EXPANDED -> COMPACT`: 접기 버튼, Esc. `COMPACT -> EVENT`: 중요 이벤트 수신, 큐 규칙 충족. `EVENT -> COMPACT`: 6초 경과. `EVENT -> EXPANDED`: 클릭; 보류 이벤트는 로그에 남김. `SETTINGS` 진입은 트레이 메뉴/확장 뷰 설정 버튼. 확장/설정 진입 시 이벤트 치환 타이머 일시 정지 혹은 소거(권장 소거); 최신 이벤트는 로그에서 확인.

### 2.2 이벤트 우선순위

1. `GAME_END` (최상)
2. `BARON`, `ELDER`, 명확히 확인된 `GOLD_LEAD_CHANGE`
3. `DRAGON_SOUL` (원천에서 확정 가능할 때), `MULTIKILL_WINDOW`
4. `DRAGON`, `TOWER`
5. `KILL`, 일반 골드 격차

동시에 2개 이상 발생하면 우선순위 높은 1건만 티커에 표시하며 나머지는 로그에 저장한다. 같은 게임에서 6초 이내 연속 중요 이벤트 수신 시 높은 우선순위로 교체하고 6초 타이머 재시작. 일반 이벤트는 기본 티커 알림 없음.

## 3. UI 상세 규격

### 3.1 최소화(270×38dp)

- 외곽 8px radius, 1px 경계, 창 장식 없음. 팝업 그림자는 선택 사항.
- 좌측 상태 표시점(라이브/대기/지연), 가운데 `T1 2 : 1 GEN`, 우측 경기 시간 `24:32`, 확장 화살표.
- 드래그 손잡이 영역 최소 폭 18px: 커서를 `move`로 표기. 클릭·드래그 충돌 방지.
- 텍스트 12~13px, 최소 가독성; 짧은 팀 약칭을 API에 없을 때 로컬 매핑.
- 좁아지면 타이머/추가 정보가 먼저 숨겨지고 팀명과 세트 스코어는 유지.

### 3.2 이벤트 바

- 같은 크기(270×38), 텍스트 한 줄 예: `T1 바론 획득 · 24:32`.
- 애니메이션은 120~180ms 페이드 전환, 기본 무음, 깜박이는 배경 금지.
- 텍스트가 길면 말줄임표, 전체 메시지는 확장 로그에서 표시.

### 3.3 확장(350×300dp)

- 헤더: 팀/세트 스코어, 접기, 설정, 상태.
- 요약: 현재 세트 번호, 경기 시간, 팀별 K/D 또는 킬, 골드, 타워, 드래곤, 바론.
- 로그: 최신순, 경기 게임 시간 `mm:ss`, 이벤트 유형, 검증 가능한 한국어 메시지.
- '최근 데이터 수신 시간'과 '방송보다 지연될 수 있음' 툴팁.
- 로그 스크롤 중 새 이벤트 수신 시 강제 스크롤 방지. 맨 위에 있을 경우에만 신규 메시지 즉시 표시.

### 3.4 설정

- 전체 불투명도: `10..100` 정수 %, `step=5`, 기본 `65`, 드래그 시 미리보기 즉시 반영, 슬라이더 키보드 방향키 지원.
- 호버 시 100% 불투명도: ON/OFF, 기본 OFF. 포인터가 실제 창 안으로 진입 시 100%로, 나가면 설정값으로 복귀(150ms 트랜지션). 호버 OFF이면 전혀 자동 변경하지 않음.
- 중요 이벤트로 투명도 강제 변경하지 않음.
- 최상단 고정 기본 ON, 트레이에서 해제 가능.
- 로그인 시 자동 실행 기본 OFF. 사용자가 명시적으로 켜는 경우에만 적용.
- 트레이 아이콘 표시, 종료 항목 항상 노출.
- 설정 저장: AppConfig(`%APPDATA%` 계열 앱 설정 경로), 원자적 파일 갱신; 보안상 민감 정보 저장 안 함.

### 3.5 DPI, 화면 경계, 다중 모니터

- 모든 위치 계산은 **논리 픽셀**로 통일. Tauri 모니터 `scaleFactor` 및 작업 영역 좌표를 사용.
- 확장 직전 현재 창 아래쪽 가장자리의 Y 좌표를 보존하되, 화면 하단 40%에 있으면 위로 확장. 그 외 아래로 확장. 화면에 맞지 않으면 작업 영역으로 클램프.
- 위치 기억은 모니터 식별 가능한 정보 + 상대 좌표 + 최소/확장 기준 앵커로 기록. 모니터가 사라진 경우 주 모니터 중앙 하단 근처로 복귀.
- 최소 글꼴 가독성 및 125/150/200% 배율 테스트.

## 4. 전체 불투명도: 구현 조건 및 우선 선택

**사용자 요구**: 배경, 글자, 아이콘, 테두리 모두 동일한 alpha(투명도) 적용. 별도의 글자 불투명 유지 기능을 기본 제공하지 않는다.

### 4.1 1차 구현 선택: Windows 레이어드 윈도우 전역 alpha

- Tauri 기본 Window API에 크로스 플랫폼 `setOpacity()`가 있다고 **가정하지 않는다**.
- Rust Windows 전용 명령 `set_window_opacity(percent: u8)` 구현.
- 인자 10~100 범위 검증 후 0..255 `BYTE alpha = round(255 * percent / 100)`로 환산.
- Win32 HWND를 확보한 뒤 창 스타일에 `WS_EX_LAYERED`를 부여하고 `SetLayeredWindowAttributes(hwnd, 0, alpha, LWA_ALPHA)` 적용.
- 명령은 Windows 빌드에서만 활성화. HWND 액세스와 레이어드 처리에 대한 Tauri/WebView2 호환성 검증 필수.
- Win32 실패 시 OS 에러코드 로깅, 사용자에게 '불투명도 조절을 적용할 수 없음' 안내, 이전 정상값 유지.
- **주의**: WebView2 투명 창과 `WS_EX_LAYERED` 조합은 OS 버전/렌더러에 따라 클릭/렌더링 문제가 생길 수 있다. 초기 기술 스파이크에서 반드시 검증한다.

### 4.2 2차 폴백: 콘텐츠 루트 전체 CSS opacity

- Windows 전역 alpha 구현이 WebView2와 충돌하면 `transparent: true` 창 및 투명 WebView 배경에서 앱 콘텐츠 **최상위 루트 하나**에 `opacity: percent/100`을 적용한다.
- `background`, `text`, `icon`, `border`가 전부 이 루트 하위에 있어야 한다. 루트 바깥에 포털/툴팁/팝오버를 렌더링하지 않는다.
- 이 방법은 **렌더된 위젯 콘텐츠 전체의 불투명도**를 맞추는 것으로, 운영체제 차원의 창 전체 alpha와는 메커니즘이 다르다. 콘텐츠 밖 투명 영역의 클릭 처리 검증 필요.
- CSS 대안이 기본 요구 수준을 충족하면 MVP는 이 방식으로도 출시 가능하지만, UI 겉모습이 같은지 스크린샷 테스트로 검증한다.

### 4.3 검증 케이스

- 흰색/검은색/컬러 배경 위 10/35/65/100% 불투명도.
- 글자/아이콘/테두리/배경 모두 설정값에 따라 함께 변하는지.
- 드래그, 클릭, 팝업, 트레이 복원, 멀티 모니터, 125~200% DPI에서 동작.
- 창 밖 투명 영역이 클릭을 가로채지 않는지.
- 호버 복원 옵션 ON/OFF, 150ms 안팎 전환, 창을 떠난 뒤 값 복원.

## 5. 데이터 공급원 검증 및 한계

후보: 비공식 LoL Esports API (`getLive`, `getSchedule`, `/window/{gameId}`, `/details/{gameId}`); 저장소 구현 예제 https://github.com/jpteixeira99/lol-esports-api , 비공식 스펙 https://github.com/vickz84259/lolesports-api-docs .

**중요**: 비공식·비보증 데이터 경로다. 실제 응답, 인증, 호출 한도, 약관·재배포 조건 및 서비스 제공 범위를 먼저 확인한다. 공개 저장소의 키를 제품 인증 키로 하드코딩하지 않는다. 합법적 접근 경로가 없거나 공급이 중단되면 라이브 모드를 비활성화하고, 리플레이/모의 데이터 모드로 개발을 계속한다. 실시간 갱신 주기와 방송 대비 지연은 보장하지 않는다.

### 5.1 공급원 어댑터 인터페이스

- `list_matches()` -> `list[MatchSummary]`
- `get_match(match_id)` -> `MatchSummary`
- `get_game_frames(game_id, after_source_timestamp)` -> `list[RawFrame]`
- `get_game_details(game_id, timestamp)` -> optional `RawDetails`
- `health()` -> availability/latency/error counters

공급원마다 응답 포맷을 달리해도 내부에는 정규화 객체만 전달한다. 특정 리그의 데이터가 지원되지 않으면 '통계 미지원' 표기; 없는 값을 0으로 위장하지 않음.

### 5.2 수집 정책

- 라이브 경기 목록: 60초마다 확인(서비스 조건에 맞게 조정).
- 진행 중 추적 게임: 기본 10초마다 최근 프레임 요청. 원본이 약 10초 단위라 같은 프레임을 중복 수집할 수 있음을 고려.
- 타임아웃: 5초. HTTP 429/5xx 시 지수 백오프 + 지터, 최소 10초·최대 120초.
- 모든 클라이언트는 중앙 서버가 캐싱한 자료를 조회한다. 사용자 수에 비례해 원본 API 요청 증가 금지.
- 프레임 수집: 최근 2개 이상 중첩 조회, source timestamp로 정렬·중복 제거, 백필(window) 처리.
- 게임 종료를 확인할 때까지 주기적 이벤트 로그 마감 처리. 세트 경계는 game ID로 분리.
- 필드가 없으면 `null` 및 `UNKNOWN`, 절대 0으로 채우지 않음.

## 6. 데이터 계약(클라이언트-서버)

### 6.1 상태 모델

```ts
type ConnectionState = 'live' | 'delayed' | 'offline';
type MatchStatus = 'scheduled' | 'live' | 'ended' | 'unknown';
type EventType = 'KILL_DELTA' | 'MULTIKILL_WINDOW' | 'DRAGON' | 'BARON' | 'ELDER' | 'TOWER' | 'GOLD_LEAD_CHANGE' | 'GAME_END';
interface MatchState {
  matchId: string;
  gameId: string | null;
  status: MatchStatus;
  connection: ConnectionState;
  league: string;
  blue: { id:string; name:string; shortName:string; seriesWins:number; kills:number|null; gold:number|null; towers:number|null; dragons:number|null; barons:number|null };
  red:  { id:string; name:string; shortName:string; seriesWins:number; kills:number|null; gold:number|null; towers:number|null; dragons:number|null; barons:number|null };
  gameNumber: number | null;
  gameTimeSeconds: number | null;
  sourceTimestamp: string | null;
  receivedAt: string;
  revision: number;
}
interface MatchEvent {
  id: string;
  matchId: string;
  gameId: string;
  type: EventType;
  gameTimeSeconds: number | null;
  occurredAt: string | null;
  observedAt: string;
  teamId: string | null;
  priority: 'normal' | 'important' | 'critical';
  messageKo: string;
  confidence: 'confirmed' | 'derived';
  sourceRevision: number;
}
```

- 모든 외부/서버 시각 UTC ISO 8601. 사용자 로컬 타임은 클라이언트에서 변환.
- `gameTimeSeconds`는 게임 내부 시계; 이벤트 실제 발생 UTC와 혼동 금지.
- `revision`은 게임별 단조 증가 정수. 동일 버전 재전송은 허용, 클라이언트가 중복 렌더링하지 않아야 함.
- 서버 반환 JSON은 camelCase; Pydantic의 alias generator로 일치.

### 6.2 REST API

- `GET /api/v1/health` -> `{status, sourceStatus, updatedAt}`
- `GET /api/v1/matches?league=worlds&status=live` -> 경기 요약 목록
- `GET /api/v1/matches/{matchId}/state` -> `MatchState` (없는 경우 404)
- `GET /api/v1/matches/{matchId}/events?limit=50&before=<cursor>` -> `{items,nextCursor}`; 최대 100
- `GET /api/v1/matches/{matchId}/stream` -> SSE

SSE 이벤트:

```text
event: state
id: 102
data: {"revision":102,"matchId":"example","...":"..."}

event: match_event
id: event-id-123
data: {"id":"event-id-123","type":"BARON","...":"..."}

: keepalive
```

- 접속 시 먼저 현재 상태와 최신 50개 이벤트를 REST로 요청하고 SSE 연결.
- SSE 재접속 시 `Last-Event-ID`를 활용하되 서버 이력 윈도 밖이면 REST 재동기화.
- 서버 이벤트 ID 및 클라이언트 `Set` 기반 중복 제거. SSE 15초 주기 heartbeat.
- 브라우저 오류·연결 끊김 시 2, 4, 8, 16, 30초 백오프(최대 30초)로 재연결.

## 7. 이벤트 감지 알고리즘

입력은 **같은 `gameId`의 서로 다른 source timestamp를 가진 연속 프레임**. 동시 발생 여부나 위치를 원본 데이터에서 알 수 없으면 추측하지 않는다.

1. raw frame 정규화 및 필수 ID/시간 검증.
2. `gameId + sourceTimestamp` 기준 정렬, 이전 프레임 조회.
3. 필드별 변화량(`current - previous`) 계산. 음수/비정상 큰 변화는 리셋 또는 데이터 정정으로 분류해 무조건 이벤트 생성하지 않음.
4. 검증 가능한 변화만 이벤트로 만든다. 예: 팀 바론 +1 -> `{team} 바론 획득`; 팀 킬 +1 -> `{team} 킬 획득`.
5. 10~20초 관측 구간 내 각 팀 킬 증가량 합계를 비교해 'T1 3킬·GEN 1킬 기록' 등 표현. '한타 승리'나 '솔로킬' 금지.
6. 골드 역전: 부호 변경 + 현재 차이 >= 500골드 + 2개 연속 프레임 유지 시 알림. 숫자는 설정 상수이며 실제 데이터 검증 후 조정.
7. 드래곤 종류, 획득 선수, 포탑 위치 등은 원본에 명시적 정보가 있을 때만 표시. 없는 경우 일반 메시지.
8. 이벤트 결정적 ID: `sha256(gameId|type|teamId|sourceTimestamp|changeIndex)`. 수집 중복·SSE 재전송에도 같은 사건은 한 건.
9. 원본이 첫 프레임만 제공된 경우 현재 누적 수치는 표시하되 과거 발생 이벤트로 소급 생성하지 않음.
10. 경기 종료: 공식 결과/게임 상태가 확인된 때에만 `GAME_END`; 임의 타임아웃으로 승자를 추정하지 않음.

정정 프레임이 들어오면 이전 이벤트 삭제를 자동 가정하지 않는다. 저장 이벤트의 `sourceRevision`을 남기고 필요할 때 correction/replace 메시지를 정의하도록 확장한다.

## 8. 클라이언트 창 제어와 권한

- `decorations:false`, `transparent:true`, `alwaysOnTop:true`, `skipTaskbar:true`, `resizable:false`.
- 트레이 아이콘에는 `보이기/숨기기`, `경기 선택`, `항상 위`, `설정`, `종료` 필수.
- 기본 닫기 동작: 창 닫기 버튼 없이 숨김. 앱 종료는 트레이 `종료`로 명시.
- 커스텀 드래그: 핸들만 드래그 시작. 스코어 클릭/슬라이더와 경합 방지.
- Tauri capability/권한 최소화: `setSize`, `setPosition`, `startDragging`, `setAlwaysOnTop`, `show`, `hide`에 필요한 권한만.
- 네트워크 호출은 서버 도메인 HTTPS만. 외부 페이지 임의 로딩, 토큰 노출, 브라우저 권한 광범위 허용 금지.
- 전체 불투명도 Win32 native 적용은 자체 Rust 명령으로 구현하고 인자 검증.

## 9. 사용자 설정 스키마

```ts
interface UserSettings {
  schemaVersion: 1;
  opacityPercent: number;              // 10..100, step 5, default 65
  brightenOnHover: boolean;            // default false
  eventDisplaySeconds: number;         // 3..15, default 6
  preferredMatchId: string | null;
  importantTypes: EventType[];
  alwaysOnTop: boolean;                // default true
  launchAtLogin: boolean;              // default false
  theme: 'light' | 'dark' | 'system';  // default light
  widgetPosition: { monitorKey:string|null; x:number; y:number } | null;
}
```

설정 스키마 버전이 달라지면 마이그레이션. 손상 파일 발견 시 기본값 복구 및 진단 로깅. 중요한 이벤트 필터는 원본 로그 저장이 아닌 **티커 노출**에만 영향.

## 10. 오류 상태 정책

| 상황 | 화면 표시 | 서버/클라이언트 동작 |
|---|---|---|
| 경기 없음 | `진행 중 경기 없음` | 60초 일정 재조회 |
| 라이브 공급원에 해당 통계 없음 | `통계 미지원` | `null` 유지 |
| 최신 프레임 수신 30초 초과 | `데이터 지연` | 마지막 수치 유지, 점 노란색 |
| 최신 프레임 수신 120초 초과 | `연결 끊김` | 회색 점, 재시도 |
| 공급원 401/403 | `데이터 접근 불가` | 원인 로그 기록, 무한 빠른 재시도 금지 |
| 공급원 429 | `갱신 일시 지연` | 지수 백오프 |
| SSE 끊김 | `재연결 중` | REST 동기화 + 재접속 |
| 업데이트 확인 실패 | 기존 버전 계속 사용 | 비파괴 알림 |

위 임계값(30/120초)은 제품 기본값이며 경기 소스 지연 측정 후 조정한다.

## 11. 프로젝트 파일 트리

```text
lol-live-widget/
  apps/
    desktop/
      src/
        components/ScoreBar.tsx
        components/EventTicker.tsx
        components/ExpandedPanel.tsx
        components/SettingsPanel.tsx
        hooks/useMatchStream.ts
        hooks/useWindowGeometry.ts
        hooks/useOpacity.ts
        state/widgetStore.ts
        types/contracts.ts
        styles/widget.css
        App.tsx
      src-tauri/
        src/main.rs
        src/window_commands.rs
        src/tray.rs
        capabilities/default.json
        tauri.conf.json
    server/
      app/main.py
      app/api/routes.py
      app/providers/base.py
      app/providers/lolesports.py
      app/collectors/poller.py
      app/events/detector.py
      app/events/formatter_ko.py
      app/models/contracts.py
      app/storage/memory.py
      tests/
  fixtures/
    raw_frames/
    expected_events/
  docs/
    implementation_spec.md
    data_source_validation.md
    api_contract.md
    test_plan.md
  README.md
```

## 12. 구현 순서와 선행 조건

### Phase 0 — 공급원/Win32 기술 타당성 스파이크 (필수)

- 가상 경기 fixture 마련.
- 공식 문서와 라이브/종료 경기 API 응답 비교: 접근성, 약관, 수집 지연, 프레임 필드.
- Tauri 투명 창에서 Win32 전역 alpha 10/65/100%, 드래그/호버/클릭 정상 동작 확인.
- 실패하면 루트 CSS 전체 opacity 폴백 검증. 해당 방식에서도 동일한 시각 요구를 충족하는지 합의.
- 이 단계 산출물: 스크린샷, 실측 지연표, 성공/실패 체크리스트, 선택한 alpha 구현 방식 기록.

### Phase 1 — 오프라인 위젯 MVP

- 가상 fixture에 연결된 Compact/Event/Expanded/Settings, 드래그, 불투명도 슬라이더, 트레이, 위치 저장 완성.
- 이벤트 타이머와 우선순위 규칙 단위테스트.

### Phase 2 — 서버 MVP

- Provider interface, 수집기, 프레임 정규화, 상태 스냅샷, 이벤트 생성, REST, SSE 구현.
- fixture replay로 시간순/중복/결측/프레임 지연 검증.

### Phase 3 — 통합 및 실제 경기 검증

- 실제 데이터로 match/game id 매핑 및 세트 교체 확인.
- 공식 중계/공식 결과와 교차검증. 데이터 최신성 지표 수집.
- 설치 파일 빌드, 새 PC 테스트, 미설치 WebView2 대응, 자동실행 OFF 확인.

## 13. 테스트 기준 및 수용 조건

| ID | 시나리오 | 기대 결과 |
|---|---|---|
| UI-001 | 최초 실행 | 하단 근처 270×38 위젯, 65% 불투명 |
| UI-002 | 슬라이더 10/65/100% | **글자·아이콘·배경·테두리 전체**에 동일 alpha 적용 |
| UI-003 | 슬라이더 조절 후 재시작 | 설정값 유지 |
| UI-004 | 마우스 호버 옵션 OFF | 절대 자동 선명화하지 않음 |
| UI-005 | 호버 옵션 ON | 진입 100%, 이탈 시 슬라이더 값 복원 |
| UI-006 | 이벤트 수신 | 창 높이 그대로 6초 텍스트 치환, 불투명도 유지 |
| UI-007 | 스코어 클릭 | 확장 패널 오픈, 로그 및 통계 표시 |
| UI-008 | 바탕화면 하단에서 확장 | 위쪽으로 펼쳐져 화면 경계 이탈 없음 |
| UI-009 | 드래그 후 재시작 | 마지막 위치 복원 |
| UI-010 | 외부 모니터 제거 후 실행 | 보이는 기본 모니터 안으로 복귀 |
| UI-011 | 배율 125/150/200% | 글꼴/슬라이더/클릭 정상 |
| UI-012 | 트레이 숨기기/다시 표시/종료 | 모두 예상대로 동작 |
| DATA-001 | 같은 프레임 3번 수신 | 중복 이벤트 0건 |
| DATA-002 | 첫 프레임 킬 누적 10 | 소급 킬 이벤트 생성하지 않음 |
| DATA-003 | 킬 3:1 증가 | '관측 구간 3킬·1킬' 표현, 한타 단정 금지 |
| DATA-004 | 원본 필드 null | 0으로 강제하지 않고 미지원 표시 |
| DATA-005 | SSE 끊김·복구 | 빠진 이벤트 재동기화, 중복 0건 |
| DATA-006 | 30초/120초 이상 프레임 지연 | 각각 지연/끊김 상태 표시 |
| DATA-007 | 새 gameId 시작 | 이전 게임 로그와 분리, 현재 스코어 갱신 |
| DATA-008 | 경기 종료 | 확인된 공식 승자만 표시 |
| OPS-001 | 원본 429 | 백오프, 과도한 요청 없음 |
| OPS-002 | 서버 재시작 | 클라이언트 연결 복구 및 상태 동기화 |
| OPS-003 | 미승인 API 사용 불가 | 모의 데이터 모드 제공, 가짜 라이브 금지 |

## 14. 출시 체크리스트 / Definition of Done

- [ ] Phase 0 결과 문서화 및 원본 데이터 사용 근거 확인
- [ ] 테스트 fixture 및 기대 이벤트 JSON 보관
- [ ] 위젯 3상태, 설정 UI, 트레이, 드래그, 위치 복원 구현
- [ ] **전체 콘텐츠** 불투명도 슬라이더 10..100/step 5/기본 65 구현
- [ ] Win32 vs CSS alpha 중 실제 채택 방식 문서화
- [ ] 30/120초 지연 표시, SSE 재연결 및 중복 제거 구현
- [ ] 킬/골드/오브젝트 오류 표현 방지 테스트 통과
- [ ] 다중 모니터 및 DPI 실기기 테스트 통과
- [ ] 설치/제거/종료가 일반 사용자에게 명확함
- [ ] 공개 배포 전 상표·데이터 권리·API 조건 검토

## 15. 추후 확장 후보 (현재 구현 제외)

- LCK/MSI 대회 선택, 관심팀 즐겨찾기, 경기 종료 요약
- 토스트/알림 시간 사용자 세분화, 윈도우 전역 단축키(승인 필요)
- Tauri 자동 업데이트(서명 및 무결성 관리)
- 서버 프로세스 멀티 인스턴스 시 Redis 등의 공유 이벤트 저장소
- 시청 지연과 이벤트 관련성을 실측한 뒤 신뢰도 기반 분석 해설

## 16. 구현 시 우선 참조할 문서

- Tauri 2 Configuration: https://v2.tauri.app/reference/config/
- Tauri window customization: https://v2.tauri.app/learn/window-customization/
- Tauri WebviewWindow JS API: https://v2.tauri.app/reference/javascript/api/namespacewebviewwindow/
- 비공식 LoL Esports API: https://github.com/vickz84259/lolesports-api-docs
- 비공식 API wrapper 및 frame 설명: https://github.com/jpteixeira99/lol-esports-api

**의사결정 원칙**: 이 문서의 사용자 경험 요구사항(특히 창 전체 불투명도 및 오탐 방지)은 구현 방법보다 상위에 있다. 공급원 및 Windows 제약으로 구현 경로가 변경되면 사유, 대체 수단, 테스트 결과를 `docs/decisions/`에 기록한다.
