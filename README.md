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

- 270×38 스코어바, 클릭하면 350×300 상세 패널, Esc로 접기.
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
- 실제 공급원: `SOURCE_MODE=live`, `SOURCE_APPROVED=true`, `LOLESPORTS_API_KEY`가 필요합니다. 승인 플래그는 권리 확인의 증거가 아니며 운영자가 실제 근거를 확보해야 합니다.
- 인증 거절은 빠른 재시도 없이 수집 중단합니다. 자격 증명 수정 후 서버를 재시작합니다.
- 공급원 adapter는 아직 실제 응답 검증을 받지 않았습니다. 응답 필드가 없으면 `null`로 표시합니다.

[구현 명세](docs/implementation_spec.md) · [API 계약](docs/api_contract.md) · [수용 테스트](docs/test_plan.md) · [기술 결정](docs/decisions/001-alpha-and-replay.md) · [검증 기록](docs/progress.md)
