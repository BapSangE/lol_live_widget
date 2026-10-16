# LoL Live Widget 구현 계획

현재 0.1.0 1차 구현과 Windows 실행 확인을 마쳤다. 단일 EXE 전달과 공개 비공식 공급원을 기본 사용 경로로 정했으며, 실제 라이브 경기 검증이 다음 작업이다.

초기 계획의 목표는 Windows 로그인 없는 스코어 위젯, 중앙 FastAPI 수집 서버, 모의 데이터 우선 개발이다. 제품 요구는 [원본 명세](implementation_spec.md)가 기준이며 실행 증거와 남은 게이트는 [progress](progress.md)에 기록한다.

## 작업과 책임

1. 기술 검증/기반: 합성 fixture, Tauri/FastAPI, whole alpha 두 backend. Windows 실기기 스파이크는 출시 선행 조건.
2. 오프라인 UI: 350×62 compact/event, 350×400 expanded, 350×300 settings, 이벤트 우선순위/6초 타이머/무음, 로그 스크롤 보존.
3. Windows shell: 트레이/손잡이/최상단/자동실행 OFF, AppConfig 원자적 설정, 모니터 상대 compact 앵커, DPI/경계 클램프.
4. 수집/저장: async Provider, 목록60초/게임10초, 5초 timeout, 429/5xx 지수 백오프10~120초, 메모리 단일 worker, 중첩 프레임/중복 제거.
5. 이벤트: 첫 프레임 소급 없음, null/reset/correction 오탐 방지, 사실만 한국어로 표현, 최대20초 킬 관측, 골드500+ 두 프레임 확인, 결정적 사건 ID.
6. 통합: 명세 REST + 원자적 /sync, SSE epoch:sequence, 1,000건 replay, 15초 heartbeat, 2/4/8/16/30초 reconnect, 30/120초 freshness, 경기 변경 늦은 응답 차단.
7. 배포: 내장 수집기 포함 portable x64 EXE + WebView2 bootstrapper, Windows CI 빌드와 frozen 서버 검사. NSIS는 별도 서버용 선택 경로. 실제 라이브/새 PC/모니터/DPI 수용 검증은 후속 작업.

## 확정한 보완

- DRAGON_SOUL 계약 추가, KILL_DELTA 이름 통일.
- 화면 mode와 connection/error를 분리.
- SSE 전송 ID와 사건 ID 분리, /sync cursor로 초기 접속 경합 해소.
- epoch 변경 시 메모리 로그/revision 초기화 후 전체 재동기화. 로그 영속 복원은 하지 않는다.
- opacity 기본 CSS, 검증용 native opt-in. 동시에 적용하지 않는다.
- 재생을 라이브로 표시하지 않는다. SOURCE_MODE=live는 SOURCE_APPROVED=true가 필요하다. 공개 공급원은 API 키 없이 실행하며 persisted 공급원만 해당 API 키가 필요하다.

## 검증

pytest + Vitest/RTL + Rust 테스트 + tsc/Vite production build. 실제 Windows 체크리스트는 [test_plan](test_plan.md), 공급원 확인은 [data_source_validation](data_source_validation.md).
