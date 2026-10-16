# LoL Live Widget

Windows 10/11용 LoL e스포츠 스코어 위젯입니다. 화면 위에 작은 창을 띄워 경기 스코어와 최근 기록을 표시합니다. Tauri 2 + React UI와 FastAPI 수집기로 구성됩니다.

**현재 단계: 0.1.0 1차 마무리 (2026-10-16).** Windows x64 무설치 EXE 빌드와 내장 서버 검사를 통과했고, 사용자가 실제 Windows에서 실행되는 것을 확인했습니다. 진행 중 경기의 연속 수신과 세트 전환은 실제 라이브 시간에 추가 검증이 필요합니다.

## Windows에서 사용하기

1. `LoL-Live-Widget.exe` 하나를 Windows PC에 복사합니다.
2. 더블 클릭하면 위젯과 내장 수집 서버가 함께 실행됩니다. Python·Node.js·Rust·별도 서버 설치나 API 키 입력은 필요 없습니다.
3. 위젯을 클릭하면 상세 기록을 펼칩니다. Esc로 접고, X 또는 트레이 메뉴의 종료로 앱을 종료합니다.

기본 데이터는 Worlds 공개 비공식 공급원입니다. 인터넷 연결이 필요하며, 진행 중 경기가 없으면 `경기 대기`와 다음 일정을 표시하고 60초마다 경기를 찾습니다. WebView2가 없는 PC에서는 처음 한 번 설치 안내가 나옵니다.

산출물은 `dist/LoL-Live-Widget.exe`입니다. GitHub Actions의 [Windows portable 빌드](https://github.com/BapSangE/lol_live_widget/actions/workflows/windows-portable.yml)에서 artifact ZIP을 받았다면 압축을 풀고 EXE만 사용하면 됩니다. 자동 업데이트와 앱 코드 서명은 포함하지 않습니다.

실행 오류 로그는 `%LOCALAPPDATA%\LoLLiveWidget\portable.log`에 남습니다. 설정은 앱 설정 폴더의 `settings.json`에 저장합니다. 상세 구성·빌드·문제 확인 방법은 [Windows 무설치 안내](docs/windows_portable.md)를 참고하세요.

## 주요 동작

- 최소화 350×62: 스코어와 현재 세트의 최신 기록 한 줄을 표시합니다. 긴 문구는 말줄임표와 툴팁을 사용합니다.
- 확장 350×400: 최소화와 같은 폭이며, 일반적인 기록 두 건을 볼 수 있도록 기록 영역을 최소 120px 확보합니다. 작은 화면에서는 내부 스크롤을 사용합니다.
- 설정 350×300: 불투명도, 항상 위, 자동 실행 등을 변경합니다. 기본 불투명도는 65%, 자동 실행은 OFF입니다.
- 손잡이로 이동하며 트레이에서 숨기기·복원·경기 선택·설정·종료를 할 수 있습니다. 중요 사건은 6초간 표시하고 기본 무음입니다.
- X는 모든 모드에서 표시됩니다. 웹 미리보기에서는 수신을 멈추고 종료 화면을 표시하며 `다시 열기`로 복귀합니다.
- 모의 데이터는 `DEMO`, 과거 경기 재생은 `REPLAY`로 구분합니다. 과거 재생은 종료 후 자동 반복하지 않습니다.

## 개발 환경

Node.js 22+, Python 3.12+, Rust stable이 필요합니다. Windows 네이티브 개발에는 Microsoft C++ Build Tools와 WebView2도 필요합니다.

```sh
npm --prefix apps/desktop ci
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e 'apps/server[test]'
```

아래 명령은 저장소 루트에서 가상환경을 활성화한 뒤 실행합니다. 이 작업 공간의 기존 가상환경은 `.venv312`입니다.

### 공개 라이브 미리보기

```sh
python scripts/run_live.py
# LCK 선택: python scripts/run_live.py --league lck
```

브라우저에서 http://127.0.0.1:1420 을 엽니다. macOS에서는 `라이브 위젯 실행.command`도 사용할 수 있습니다. Ctrl+C로 UI 개발 서버와 수집기를 함께 종료합니다. 미리보기 실행은 8000·1420 포트를 사용하므로 이전 실행을 먼저 종료하세요.

### 다운로드한 실제 LCK 경기 재생

```sh
python scripts/run_lck_replay.py
```

macOS의 `LCK 리플레이 실행.command`도 같은 작업을 수행합니다. GEN–HLE 2026-09-13 1세트의 약 69초 샘플을 원래 간격으로 재생하며 킬 스코어가 3:3에서 4:4로 바뀝니다. 전체 경기 녹화가 아니며 게임 시계는 원본에 없어 `--:--`로 표시합니다. 재생 중에는 외부 요청이나 API 키가 필요 없습니다.

종료 후 마지막 통계를 유지하고 `재생 구간 종료`를 표시합니다. 처음부터 다시 보려면 Ctrl+C 후 명령을 다시 실행합니다. 브라우저 새로고침은 서버의 현재 위치에 연결합니다. 이 명령은 과거 경기 전용이며 라이브 경기로 자동 전환하지 않습니다. 원본과 검증 기록은 [LCK 캡처 검증](docs/lck_2026_capture_test.md)에 있습니다.

### UI만 확인 / 네이티브 개발

```sh
# 서버 없는 내장 모의 데이터 UI
npm --prefix apps/desktop run dev

# Tauri 네이티브 앱
npm --prefix apps/desktop run tauri -- dev
```

일반 개발 UI와 Tauri의 기본 실행은 모의 데이터입니다. 서버에 연결하려면 `apps/desktop/.env.local`에 `VITE_SERVER_URL=http://127.0.0.1:8000`을 지정한 뒤 개발 서버를 다시 실행합니다. `.env.example`은 참고용입니다. 공개 라이브 런처와 Windows portable은 필요한 연결 설정을 자동으로 전달합니다.

## 데이터 공급원과 제한

기본 라이브 경로는 공개 일정 HTML의 `ApolloSSRDataTransport` 경기 JSON과 `feed.lolesports.com`의 통계 feed를 읽습니다. 웹페이지 JavaScript를 실행하거나 다른 저장소의 키를 복사하지 않습니다. 공식 API 접근 승인을 기다리지 않고 사용하는 개인용 비공식 경로이며, 공개 페이지 형식·접근 정책 변경으로 수집이 중단될 수 있습니다.

- 독립 서버: `SOURCE_MODE=live`, `SOURCE_APPROVED=true`, `LIVE_PROVIDER=public`, `LIVE_LEAGUES=worlds`. 공개 경로는 API 키를 읽거나 전송하지 않습니다.
- 기존 persisted 어댑터는 선택 사항입니다. `LIVE_PROVIDER=persisted`와 해당 API용 `LOLESPORTS_API_KEY`가 필요하며 `RGAPI-` Riot Developer 키는 호환되지 않습니다.
- 일정 캐시로 경기 발견·세트 전환이 늦을 수 있습니다. 통계는 현재 시각보다 약 20초 전까지 조회하며, 이는 방송 대비 실측 지연이 아닙니다. 제공되지 않는 값은 `null`로 취급합니다.
- 공개 일정과 과거 경기 feed는 실제 응답으로 확인했습니다. **진행 중 경기의 지속 수신·종료·다음 세트 전환은 아직 미검증입니다.** [공개 공급원 검증 기록](docs/unofficial_live_validation.md)을 참고하세요.

## 검사와 빌드

```sh
python -m pytest apps/server/tests
npm --prefix apps/desktop run check
npm --prefix apps/desktop test -- --run
npm --prefix apps/desktop run build
cargo test --locked --manifest-path apps/desktop/src-tauri/Cargo.toml
```

Windows x64에서 단일 EXE를 생성합니다.

```powershell
python -m pip install "pyinstaller>=6.10,<7"
python scripts/build_windows_portable.py
```

의존성 설치가 선행되어야 합니다. 산출물은 `dist/LoL-Live-Widget.exe`이며 `--demo`로 오프라인 UI, `--smoke-test`로 내장 서버를 검사할 수 있습니다. [Windows 빌드 상세](docs/windows_portable.md)를 참고하세요.

별도 서버에 연결하는 NSIS 설치형 클라이언트도 `npm --prefix apps/desktop run tauri -- build`로 빌드할 수 있습니다. 서버 origin은 빌드 시 `VITE_SERVER_URL`로 지정하며 CSP에 반영됩니다. 결과는 `apps/desktop/src-tauri/target/release/bundle/nsis/`에 생성됩니다. 단일 EXE 전달에는 portable 빌드를 사용합니다.

API 계약을 변경했다면 함께 재생성합니다.

```sh
python scripts/export_contract.py
npm --prefix apps/desktop run generate:contracts
```

## 저장소와 서버 운영

| 경로 | 역할 |
| --- | --- |
| `apps/desktop` | React UI와 Tauri Windows shell |
| `apps/server` | 공급원, 이벤트 감지, 메모리 저장소, REST/SSE |
| `scripts` | 라이브·리플레이 실행과 Windows 패키징 |
| `fixtures` | 모의 데이터와 출처를 기록한 실제 경기 샘플 |
| `docs` | 계약, 설계, 검증 기록과 남은 테스트 |

독립 서버는 `python -m uvicorn app.main:app --app-dir apps/server --host 127.0.0.1 --port 8000`으로 실행합니다. 설정은 환경변수 또는 uvicorn `--env-file`로 전달합니다. 기본은 모의 데이터입니다.

저장소가 메모리 기반이므로 worker는 1개만 사용합니다. 서버 재시작 시 로그와 revision이 초기화되며 클라이언트는 새 epoch로 재동기화합니다. 외부 배포에는 HTTPS reverse proxy를 사용하고 SSE 버퍼링을 끄며 idle timeout을 heartbeat 15초보다 길게 설정합니다. Docker 빌드는 `docker build -f apps/server/Dockerfile -t lol-widget-server .`입니다.

## 다음 확인 사항

1. 실제 라이브 시간에 경기 발견 → 스코어·기록 갱신 → 세트 전환 → 종료 흐름 확인.
2. Windows에서 X·트레이 종료, 설정 재시작 유지, 자동 실행 ON/OFF 확인.
3. DPI 125/150/200%, 다중 모니터, WebView2 없는 PC 확인.

[현재 상태·변경 기록](docs/progress.md) · [수용 테스트](docs/test_plan.md) · [구현 명세](docs/implementation_spec.md) · [구현 계획](docs/implementation_plan.md) · [API 계약](docs/api_contract.md)
