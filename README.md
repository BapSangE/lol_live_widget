# LoL Live Widget

Windows 10/11용 LoL 스코어 위젯. Tauri 2 + React / 중앙 FastAPI 수집 서버.

현재 기본 실행은 **모의 데이터**입니다. 승인된 데이터 공급원 접근 없이는 라이브로 전환하지 않습니다. Windows 전용 창 동작과 설치 프로그램은 Windows 실기기/VM 수용 테스트를 통과한 뒤 출시해야 합니다.

## 준비

- Node.js 22+, Python 3.12+, Rust stable
- Windows 개발: Microsoft C++ Build Tools와 WebView2
- 의존성 설치:

```sh
npm --prefix apps/desktop ci
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e 'apps/server[test]'
```

## 실행

서버 없이 내장 fixture를 사용하는 UI:

```sh
npm --prefix apps/desktop run dev
# http://127.0.0.1:1420
```

Windows 데스크톱 위젯:

```sh
npm --prefix apps/desktop run tauri -- dev
```

중앙 모의 데이터 서버:

```sh
python -m uvicorn app.main:app --app-dir apps/server --host 127.0.0.1 --port 8000
```

서버 통합을 확인하려면 `apps/desktop/.env.local`에 `VITE_SERVER_URL=http://127.0.0.1:8000`을 지정하고 개발 서버를 다시 실행합니다. `.env.example`은 참고 파일이며 자동으로 적용되지 않습니다. 서버 설정은 환경변수 또는 uvicorn의 `--env-file`로 전달합니다.

## 동작

- 최소화 350×62: 위쪽 스코어바와 아래쪽 최신 경기 기록 한 줄. 클릭하면 같은 폭의 350×400 상세 패널, Esc로 접기. 설정 패널은 350×300입니다.
- 상세 패널은 기록 영역을 최소 120px 확보해 통계를 펼쳐도 일반적인 기록 두 건을 함께 볼 수 있습니다. 화면이 작으면 작업 영역에 맞추고 내부 스크롤을 사용합니다.
- 아래 기록은 현재 세트의 최신 1건을 유지하고 새 기록이 들어오면 교체합니다. 긴 문구는 말줄임표로 표시하며 전체 문구는 툴팁·상세 패널에서 확인합니다.
- 손잡이로 이동. 트레이에서 숨기기·경기 선택·항상 위·설정·종료.
- 불투명도 10~100%, 기본 65%. 글자와 아이콘을 포함한 전체 콘텐츠에 적용.
- 기본 무음, 중요 사건 6초 치환. 이벤트가 불투명도를 바꾸지 않습니다.
- 재생 데이터 종료 후 자동 반복하지 않습니다. 브라우저 새로고침/앱 재시작으로 처음부터 재생합니다.
- 네이티브 설정은 앱 설정 폴더 `settings.json`에 원자적으로 저장합니다. 브라우저 미리보기는 localStorage를 사용합니다.

## 검증

```sh
python -m pytest apps/server/tests
npm --prefix apps/desktop run check
npm --prefix apps/desktop test -- --run
npm --prefix apps/desktop run build
cargo test --locked --manifest-path apps/desktop/src-tauri/Cargo.toml
```

API 계약 재생성:

```sh
python scripts/export_contract.py
npm --prefix apps/desktop run generate:contracts
```

## Windows 설치 프로그램

Windows에서 `npm --prefix apps/desktop run tauri -- build`를 실행합니다. 기본 빌드는 내장 모의 데이터 버전입니다. 라이브 클라이언트 빌드는 승인된 서버를 배포하고 `VITE_SERVER_URL`에 실제 HTTPS origin을 지정해야 합니다. 빌드 스크립트가 CSP를 해당 origin으로 제한합니다.

결과: `apps/desktop/src-tauri/target/release/bundle/nsis/*.exe`. CI도 같은 설치 파일을 artifact로 생성합니다. WebView2가 없으면 설치 프로그램이 런타임을 다운로드하므로 인터넷 연결이 필요합니다. 자동 업데이트와 코드 서명은 이 MVP에 포함하지 않습니다.

## 서버 배포와 제한

- 저장소는 메모리입니다. **worker는 반드시 1개**만 실행합니다.
- 서버 재시작 시 이벤트 로그/revision이 초기화되며 클라이언트는 새 epoch로 재동기화합니다.
- HTTPS reverse proxy를 사용하고 SSE 버퍼링을 끕니다. idle timeout은 heartbeat 15초보다 길게 설정합니다.
- Docker: 저장소 루트에서 `docker build -f apps/server/Dockerfile -t lol-widget-server .`.
- 공개 비공식 공급원: `SOURCE_MODE=live`, `SOURCE_APPROVED=true`, `LIVE_PROVIDER=public`, `LIVE_LEAGUES=worlds`를 지정합니다. 공개 일정 HTML과 경기 통계 feed를 읽으며 API 키는 사용하지 않습니다.
- 기존 persisted API를 사용하려면 `LIVE_PROVIDER=persisted`와 해당 API용 `LOLESPORTS_API_KEY`가 필요합니다. `RGAPI-` Riot Developer 키로는 이 API에 접근할 수 없습니다.
- 인증 거절은 빠른 재시도 없이 수집 중단합니다. 자격 증명 수정 후 서버를 재시작합니다.
- 공개 일정과 과거 경기 feed는 실제 응답으로 검증했습니다. 진행 중 경기의 지속 수집과 세트 전환은 실전 검증이 남아 있습니다. 응답 필드가 없으면 `null`로 표시합니다.

[구현 명세](docs/implementation_spec.md) · [API 계약](docs/api_contract.md) · [수용 테스트](docs/test_plan.md) · [기술 결정](docs/decisions/001-alpha-and-replay.md) · [검증 기록](docs/progress.md)

### 다운로드한 2026 LCK 경기로 테스트

macOS에서는 저장소의 `LCK 리플레이 실행.command`를 더블 클릭하거나 아래 명령을 실행합니다. 현재 작업 공간에 설치된 Python/Node를 사용합니다.

```sh
.venv312/bin/python scripts/run_lck_replay.py
```

브라우저에서 http://127.0.0.1:1420 을 열고 위젯을 클릭해 펼치면 LCK / GEN–HLE 1세트가 표시됩니다. 실행 시점부터 약 69초 동안 원래 시간 간격으로 재생합니다. 킬은 3:3에서 4:4로 바뀌고 관련 기록이 나타납니다. 종료 후 마지막 통계를 유지하며 `재생 구간 종료`를 표시합니다. 다시 처음부터 보려면 실행한 터미널에서 Ctrl+C를 누른 뒤 같은 명령을 다시 실행합니다. 브라우저만 새로고침하면 서버의 현재 재생 위치에 연결됩니다.

실제 다운로드한 원본 및 정규화 데이터는 `fixtures/captures/lck-2026-09-13-gen-hle-game1/`에 있습니다. 2026-09-13 경기의 약 70초 샘플이며 전체 경기 녹화가 아닙니다. 게임 시계는 원본에서 제공하지 않아 `--:--`로 표시합니다. 화면의 ‘재생’ 시간은 샘플 내 경과 시간입니다. 원본 다운로드 후 재생 중에는 외부 데이터 요청이나 API 키가 필요하지 않습니다.

이 실행 명령은 **과거 경기 재생 전용**입니다. 실제 경기가 시작해도 새 경기로 자동 전환하지 않습니다. 실제 경기 탐색은 아래의 별도 라이브 실행 명령을 사용합니다. API 키 없이 과거 feed를 읽은 결과는 진행 중 경기의 연속 수집까지 검증됐다는 의미가 아닙니다.

### 공개 비공식 API로 라이브 실행

macOS에서는 `라이브 위젯 실행.command`를 더블 클릭하거나 다음을 실행합니다.

```sh
.venv312/bin/python scripts/run_live.py
```

http://127.0.0.1:1420 에서 Worlds 위젯을 확인합니다. API 키를 읽거나 전송하지 않습니다. 진행 중 경기가 없으면 다음 일정과 `경기 대기`를 표시하며, 실행을 유지하면 60초마다 새 경기를 찾습니다. 종료는 실행 터미널에서 Ctrl+C입니다. 리플레이와 같은 포트를 사용하므로 이전 실행을 먼저 종료해야 합니다.

LCK를 선택하려면 `.venv312/bin/python scripts/run_live.py --league lck`를 사용합니다. 현재 실제 일정 응답 검증은 Worlds 기준이며 다른 리그는 실제 경기 검증이 필요합니다.

이 경로는 공개 페이지의 `ApolloSSRDataTransport` 경기 JSON을 해석하고 `feed.lolesports.com`의 10초 통계 구간을 수집합니다. 웹페이지 JavaScript 실행이나 다른 저장소의 키 복사는 하지 않습니다. 공개 페이지가 캐시되면 경기 발견·세트 전환이 늦을 수 있습니다. feed는 현재 시각보다 약20초 전까지 조회하며, 이 값은 방송 대비 실측 지연이 아닙니다. 페이지 형식 변경·접근 거절은 공급원 오류로 처리합니다.

2026-10-16 확인: 공개 일정 40건, 진행 중 Worlds 0건, 다음 일정 한국 시간 10월17일 03:00. 따라서 실제 라이브 스코어의 연속 갱신까지 검증된 상태는 아닙니다. 자세한 기록은 [공개 공급원 검증](docs/unofficial_live_validation.md)을 참고합니다.
