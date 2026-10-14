# ADR 001 — 불투명도 및 재생 우선 개발

현재 개발 호스트는 macOS. Windows HWND/WebView2 상호작용과 실기기 DPI·모니터 동작은 미검증이다.

기본 구현은 transparent 창 + 최상위 콘텐츠 루트 전체 CSS opacity. 모든 배경·글자·아이콘·테두리·안내는 루트 안에 있으며 외부 portal을 사용하지 않는다. native alpha와 CSS alpha는 동시에 적용하지 않는다.

Windows 실험용 `LOL_WIDGET_NATIVE_ALPHA=1` 환경변수를 명시하면 자체 Rust 명령이 WS_EX_LAYERED / LWA_ALPHA를 적용한다. 기존 확장 스타일은 보존하며 실패 시 원복한다. alpha는 round(255×percent/100). Windows 검증 전 native를 기본으로 선택하지 않는다.

미승인 공급원 접근은 라이브 수집을 중단한다. 기본 서버는 ReplayProvider, 서버 URL 미설정 desktop은 내장 fixture 재생이다. 두 경로 모두 DEMO/모의 데이터 표시.

출시 전 Windows 10/11에서 10/35/65/100%와 흰색/검은색/컬러 배경, 투명 영역 클릭, 드래그, 트레이, 팝업, 125/150/200% DPI를 검증한다. 선택한 방식과 스크린샷을 이 문서에 추가한다. 현재 Windows 검증 결과는 없음.
