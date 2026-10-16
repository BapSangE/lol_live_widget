# LoL Live Widget — 1차 완료 및 검증 기록

## 2026-10-16 v0.2.0 응원 팀 알림

- 설정에 응원 팀 선택·다음 일정 표시 추가. 현재 리그에서 발견한 팀과 저장한 팀을 선택 목록으로 제공함.
- 앱 실행 중 해당 팀의 라이브 경기를 발견하면 15초 무음 위젯 팝업, 확장 및 숨김 해제, 경기 수신 연결 자동 전환을 수행함. 최초 발견 시 이미 라이브면 진행 중으로 안내함.
- 최근 50개 경기의 알림 이력을 설정에 저장해 재실행·세트 변경·재연결 중복을 방지함. 이후 수동 경기 선택은 유지함.
- OS 알림 센터가 아닌 위젯 자체 알림. 앱 종료 중 알림은 제공하지 않음. 공개 일정과 라이브 상태 갱신 지연의 영향을 받음.
- 기존 v1 설정의 새 필드 누락을 기본값으로 복원하며 프런트엔드와 Rust가 팀 정보·이력을 검증함.
- UI 30/30, Rust 6/6, TypeScript 및 Vite production 빌드 통과. Mac v0.2.0 APP/DMG 빌드 후 실제 앱 실행, 이전 설정 유지, 응원 팀 선택 UI를 확인하고 촬영함. 실제 라이브 알림과 숨김 해제의 OS별 수용 검증은 남아 있음.

## 2026-10-16 첫 GitHub Release 배포 정리

- 루트의 개발용 `.command` 런처 2개를 제거함. 공개 라이브/실제 경기 샘플 재현은 `scripts/run_live.py`, `scripts/run_lck_replay.py`로 유지함.
- README 상단에 Windows EXE·macOS arm64 DMG 직접 다운로드와 릴리스 링크를 추가함. Actions artifact 다운로드는 일반 사용자 사용 경로에서 제외함.
- Windows는 소스 `74dc522`의 성공한 [portable CI 빌드](https://github.com/BapSangE/lol_live_widget/actions/runs/38860073574) 산출물, Mac은 사용자 실행 확인을 마친 동일 기능의 로컬 DMG를 배포 대상으로 준비함.
- [v0.1.0 Release](https://github.com/BapSangE/lol_live_widget/releases/tag/v0.1.0)에 EXE·DMG·SHA256SUMS.txt 게시 완료. 공개 체크섬 다운로드와 업로드 digest 일치를 확인함.

## 2026-10-16 macOS 앱 패키징 및 문서 정리

- Apple Silicon용 `.app`과 전달용 단일 `.dmg` 생성. 공개 피드 수집기를 앱 Resources에 포함하며 별도 런타임이나 API 키 없이 실행함.
- Tauri가 수집기를 시작하고 동적 loopback 주소로 연결하며 앱 종료 시 자식 프로세스를 정리함. Windows의 외부 EXE 런처 경로는 유지함.
- macOS Release 빌드와 패키징 완료. 내장 frozen 서버 smoke test 통과, 네이티브 앱 실행과 최소화·확장·설정 화면 확인.
- 사용자도 macOS 앱 실행을 확인함. 실제 라이브 경기 연속 수집·세트 전환은 별도 미검증이며 자동 실행과 종료 후 프로세스 정리는 실기기 체크리스트에 남김.
- 코드 서명·공증 없는 개인용 arm64 빌드. Intel Mac과 Developer ID 배포는 포함하지 않음.
- 커밋 전 재검증: 서버 43/43, macOS portable feature Rust 5/5, 변경 Python Ruff 및 diff 공백 검사 통과. UI 코드는 변경하지 않았으며 앞선 패키징에서 UI 25/25와 production 빌드를 확인함.
- README를 실제 앱 스크린샷, 기능 표, OS별 실행 안내, 개발·검증 문서 링크 중심으로 재구성함. 이미지는 진행 중 경기 없는 대기 상태이며 사용자 설정을 변경하지 않고 촬영함.

## 2026-10-16 글자 크기 설정

- 기본 100% / 크게 120% / 아주 크게 140%를 추가. 경기 스코어·기록·설정에 공통 적용하며 설정을 저장함.
- 폭은 모든 모드 350px 유지. 최소화/확장/설정 높이는 각각 62/400/300px에 비율을 적용해 올림. 큰 화면의 140%는 87/560/420px이며 작업 영역보다 크면 제한함.
- 기존 v1 설정에 필드가 없어도 100%로 복원하며 다른 설정을 유지. 프런트엔드와 Rust가 동일한 세 가지 값만 허용.
- 하단 기준 확장·크기 변경·드래그 위치 보정에 변경된 최소화 높이를 사용함.
- 회귀 검증: 글자 크기 선택·저장·다시 열기, 이전 설정 호환, 잘못된 값, 확대 창의 작업 영역 제한과 하단 유지. 초기 설정 로드 시 위치 누적 이동 방지, 확대 후 위치 저장·재시작 복원, DPI 이벤트 시 재클램프를 추가 검증함.
- 로컬 재검증: 서버 42/42, UI 25/25, Rust 5/5, TypeScript/Vite build 통과. 브라우저 140%에서 폭 350px, 확장 높이 560px, 기록 영역 약 211px를 확인함. Windows 패키징은 해당 변경을 포함해 다시 실행함.

## Windows 1차 마무리 기록 — 2026-10-16 / 0.1.0

- 사용자 확인: 전달한 단일 EXE가 실제 Windows에서 정상 실행됨. 세부 OS·DPI·트레이·자동 실행 결과는 별도 확인하지 않았으므로 통과로 간주하지 않음.
- 구현 완료: 최소화 최신 기록 한 줄, 확장 기록 두 건 공간, 동일 가로 폭 350px, 모든 모드 X 종료, 공개 비공식 공급원, 단일 EXE와 내장 수집기.
- Windows CI: 서버 42건·UI 19건, release 빌드, 완성 EXE의 frozen 서버 smoke test 통과. Rust 4건은 앞선 Windows 빌드에서 통과.
- 검증한 빌드: `80779f204c9fe1a3f4f9eecb091405db51a772f9`, [성공한 실행](https://github.com/BapSangE/lol_live_widget/actions/runs/38840609609).
- 전달 EXE: `LoL-Live-Widget.exe`, 25,505,048 bytes. SHA-256: `e58403c8641919958062c624e9facc21898b85252b5fa17762a9c706de0491b0`.
- 기본 portable은 Worlds 공개 라이브, 일반 개발 기본값은 모의 데이터. 공개 경로는 API 키를 사용하지 않음.
- 다음 작업: 진행 중 경기의 지속 수집·세트 전환·종료 확인. X/트레이 종료·설정 저장·자동 실행·DPI/다중 모니터·새 PC WebView2 설치는 [수용 테스트](test_plan.md)에 남김.
- 1차 정리는 문서 갱신과 런처 타입 표기·Rust 서식 정리이며, 이미 전달한 EXE의 동작을 변경하지 않음.
- 정리 후 로컬 재검증: 서버 42/42, UI 19/19, Rust 4/4, TypeScript/Vite production 빌드, Ruff, 문서 상대 링크와 전달 EXE 해시 확인 통과. 서버 테스트의 upstream Starlette/httpx deprecation 경고 1건은 기존 항목.

## 이전 구현 기록

아래 내용은 각 작업 당시의 기록이다. 미실행·미배포·크기·테스트 수 등은 이후 변경될 수 있으며, 최신 상태는 위 요약과 README를 기준으로 한다.

## 2026-10-16 expanded history space and shared width

- Set compact and expanded width to 350px; compact remains 62px high, expanded is 400px, settings remains 300px.
- Expanded history reserves at least 120px for two ordinary records, with body scrolling on small work areas. Native geometry and initial size use the same dimensions.
- Desktop 19/19, Rust 3/3, TypeScript/Vite build pass. Browser measurements confirm compact 350×62, expanded 350×400 and a 120px history area with full statistics and archive notice visible.

## 2026-10-16 compact latest record

- Added a persistent latest-record row below the compact scorebar; current match/game only, ellipsis + full tooltip, click to expand history.
- Compact window is now 270×62. Updated native initial size, screen clamping, expansion bottom anchor and moved-window persistence calculations together.
- Verified in browser with the actual LCK archive: GEN/HLE score above, latest kill-window record below, retained after ticker expiry. Restored public live waiting mode after playback verification.
- Desktop 19/19, Rust 3/3, TypeScript/Vite production build pass. Windows runtime/DPI checks remain pending.

## 2026-10-16 public unofficial source

- Added opt-in `LIVE_PROVIDER=public`: public schedule HTML discovery and keyless stats feed. No page JavaScript execution or copied API keys.
- Added `scripts/run_live.py` and `라이브 위젯 실행.command`; existing LCK replay launcher retained.
- Real local HTTP: live mode healthy, 40 upcoming Worlds matches, no ongoing match at verification. Next listed start is 2026-10-17 03:00 KST.
- Fixed feed window advancement, empty-gap recovery, terminal-frame ingestion and shared discovery retry behavior; corrected connected/no-match UI to 경기 대기.
- Fresh verification: server 40/40, desktop 17/17, TypeScript/Vite production build, changed Python Ruff checks and diff whitespace checks pass.
- Live match score/event progression remains pending an actual ongoing match. See [public source validation](unofficial_live_validation.md) for evidence and known limitations.

- Baseline: 67a5022, README only; branch feat/lol-live-widget-mvp.
- Ruling: Use an isolated feature branch in the current checkout rather than another worktree. The workspace is empty and user authorized implementation; cost: changes visible in this checkout.
- Ruling: Phase 0 Windows validation cannot execute on this macOS host. Implement both alpha backends and Windows CI, keep native alpha opt-in until hardware verification. Cost: Windows release remains gated.
- Ruling: Provider credentials and approval absent. Live mode fails closed; replay is the default and visibly labelled. Cost: actual live adapter response compatibility remains unverified.
- Interfaces: detector emits MatchEvent to memory store; REST and SSE consume immutable snapshots; /sync supplies cursor to desktop stream. Shared contracts include DRAGON_SOUL.
- 당시 작업 목록: foundations → offline UI → native window/settings → collector → detector → sync integration → packaging/docs (현재 구현 완료).

- Detector RED: 5 failures, then 6/6 pass. Store RED: 5 missing behaviors, then 11/11 server suite pass.
- API RED: 2 missing endpoint failures, then 13/13 server suite pass.
- Client policy RED: 5 failures, then 5/5 pass. Stream/store RED: 2 failures, then 7/7 pass. UI RED: 2 failures, then 9/9 pass.
- OpenAPI generated; TypeScript directly aliases generated schemas.
- Typecheck initially failed because nullable Pydantic defaults become optional request fields in OpenAPI. stat formatter now treats undefined as unsupported as well as null.
- Rust SDK diagnosis: installed macOS27 SDK incompatible with current linker; SDKROOT=MacOSX15.4.sdk compiles and Rust tests pass 3/3. No system SDK changes.
- Desktop production bundle built; browser compact/expanded rendered with DEMO label.
- Ruling: Native backend opt-in, CSS default until Windows spike evidence; avoids treating platform compatibility as proven.

## Final review and verification

- Fresh reviewer: no Critical findings, five Important findings. All five reproduced with regression tests and fixed:
  - independent 60-second discovery / next live match switching;
  - observation chronology retains new-game events when prior history fills capacity;
  - first native alpha failure retains CSS opacity until native handoff succeeds;
  - ended summary keeps polling until terminal frame ingestion;
  - epoch replacement clears old pagination cursor.
- Additional RED→GREEN: reconnect permits new live ticker events; unknown settings version resets safely; rolling 20-second kills span adjacent frames; null correction breaks counter continuity.
- Pagination test fixture changed to a >20-second gap to avoid newly required aggregate events while independently testing cursor order.
- Final: minor (deferred): provider-specific health last_error is not assigned on all failures; authoritative top-level health/sourceError still reports the collector error.
- Final: minor (deferred): previous-history button can remain visible after cursor exhaustion and repeat an empty page.
- Latest local verification: server 20/20; desktop 15/15; Rust 3/3; TypeScript check and production Vite build pass.
- Expected failure-path console messages occur in client tests. Server suite emits one upstream Starlette/httpx deprecation warning, not a test failure.
- Actual local HTTP: matches and /sync returned valid replay JSON; SSE emitted state with epoch cursor. Intentional two-second stream sampling ended with curl timeout 28 because stream stays open.
- Ruling: Keep feature branch unmerged and unpublished. Implementation authorization does not require remote publishing; cost: user still needs to choose integration/deployment.
- Ruling: Two low-impact review notes deferred as above. Cost: provider sub-health may be optimistic, and exhausted history button can perform redundant reads.

## Status

- Foundations, offline UI, collector, detector, REST/SSE integration: implemented and locally verified.
- Windows commands, tray, atomic settings, geometry, installer configuration and Windows CI: implemented; host Rust compilation/unit tests pass. Windows build/runtime/installer/hardware checks remain unexecuted.
- Phase 0 Windows screenshot/alpha choice evidence: pending Windows hardware/VM.
- Actual live API validation, credentials/rights, official-match comparison and public release: pending; live mode fails closed without approval/key.
- CI workflow is prepared but not dispatched; no Windows installer artifact has been produced in this session.

- Code formatting normalized with Prettier/Ruff; Ruff check passes. Broad collector catches are intentional provider-boundary isolation.

## 2026 LCK capture validation

- Selected 2026-09-13 LCK final GEN–HLE game1 from public official schedule HTML; no web-app code execution or key extraction.
- Archived 7 contiguous windows (~69.263s, 363 raw frames / 333 unique / 30 identical duplicates), matching kill details, and independent terminal snapshot with SHA-256 provenance.
- Actual observed scorers: HLE Kanavi (Naafiri) +1, GEN Duro (Milio) +1. Cross-feed K/D/A matches.
- RED: direct detector omitted MULTIKILL_WINDOW because duplicate frames cleared its pending window. GREEN: exact duplicate returns without correction handling; capture regression passes.
- Ruling: Test only the acquired ~70-second sample and separate final snapshot. Do not call this full-game, live, or desktop playback verification; cost: those need further coverage.
- Fixture characterization: revision counts unique accepted frames (333), not raw transport frames (363). SSE test consumes response.read() before inspecting content.
- Server verification updated to 27/27; source capture report is docs/lck_2026_capture_test.md.
