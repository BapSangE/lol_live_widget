# Windows 무설치 실행 파일

[Windows EXE 다운로드](https://github.com/BapSangE/lol_live_widget/releases/latest/download/LoL-Live-Widget.exe) · [릴리스 안내](https://github.com/BapSangE/lol_live_widget/releases/latest)

**2026-10-16 1차 완료:** Windows CI 빌드·frozen 서버 검사 통과, 사용자 Windows PC 실행 확인. 실제 라이브 수신과 세부 창 동작은 [수용 테스트](test_plan.md)에서 별도 확인한다.

산출물은 `LoL-Live-Widget.exe` 한 개다. 사용자는 Node.js, Python, Rust나 별도 수집 서버를 설치하지 않는다. EXE를 더블 클릭하면 로컬 공개 데이터 수집기와 위젯을 함께 시작하고, 위젯의 X 또는 트레이 종료로 둘 다 종료한다.

## 구성

- PyInstaller one-file 런처가 Python 런타임, FastAPI 수집기, React UI를 포함한 Tauri 실행 파일, 서명을 확인한 Microsoft WebView2 설치 도구를 포함한다.
- 실행 시 임시 폴더로 내부 파일을 풀고 빈 loopback 포트를 잡아 수집 서버를 띄운다. 그 포트를 자식 위젯 프로세스 환경변수로 전달한다. 외부 인터페이스에는 서버를 열지 않는다.
- 위젯은 Rust 명령으로 검증된 `127.0.0.1` origin만 읽는다. 휴대용 빌드의 CSP는 이 loopback 통신만 추가 허용한다.
- 정상 종료 시 위젯 자식 프로세스와 수집 서버를 정리한다. 설정과 로그는 사용자 앱 데이터에 남는다. 비정상 강제 종료 경로는 Windows 실기기 검증이 필요하다.
- 기본 모드는 Worlds 공개 라이브 수집이며 API 키를 사용하지 않는다. `--demo` 인자로 오프라인 모의 데이터를 선택할 수 있다.
- WebView2가 없는 PC는 첫 실행에 Microsoft 구성요소 설치 여부를 묻는다. 이 경우 인터넷이 필요하다. 설치된 PC에서는 바로 위젯을 실행한다.
- 로그인 자동 실행은 내부 임시 실행 파일 대신 사용자가 전달받은 런처 EXE 경로를 등록한다. 이후 EXE를 이동하면 자동 실행 설정을 다시 적용해야 한다.
- 웹 미리보기의 X는 브라우저 탭을 강제로 닫는 대신 수신을 멈추고 종료 화면을 표시한다. Windows 앱의 X는 프로세스를 종료한다.

## 빌드 및 검증

Windows x64 빌드 환경에서 Node.js, Rust, C++ Build Tools와 Python 3.12를 준비하고 프로젝트 의존성 및 PyInstaller 6을 설치한다.

```powershell
npm.cmd --prefix apps/desktop ci
python -m pip install -e "apps/server[test]" "pyinstaller>=6.10,<7"
python scripts/build_windows_portable.py
```

산출물: `dist/LoL-Live-Widget.exe`.

`Build portable Windows widget` GitHub Actions 워크플로도 같은 절차를 실행한다. 완성 EXE의 `--smoke-test`는 Python 미설치 상황의 frozen 수집기 구동, 내장 fixture, REST 응답, 종료를 검사한다. 테스트는 UI/WebView 입력이나 Windows DPI 수용 테스트를 대신하지 않는다.

더블 클릭 실행은 사용자 Windows PC에서 확인했다. 실시간 연결, X 종료, 트레이 종료, 자동 실행, 새 PC의 WebView2 설치와 DPI는 추가 확인 항목이다. 앱 코드 서명은 적용하지 않는다.

## 실행 옵션과 문제 확인

```powershell
.\LoL-Live-Widget.exe --demo
.\LoL-Live-Widget.exe --smoke-test
```

- 일반 실행은 Worlds 라이브, `--demo`는 인터넷 없이 모의 UI를 확인한다.
- `--smoke-test`는 창을 열지 않고 내장 서버를 검사한다. 성공하면 `%LOCALAPPDATA%\LoLLiveWidget\portable-smoke.json`에 결과를 남긴다.
- 오류 로그는 `%LOCALAPPDATA%\LoLLiveWidget\portable.log`에 남는다.
- `portable`은 설치 프로그램 없이 실행하는 방식이다. 첫 실행의 임시 압축 해제와 설정·로그 저장은 수행한다. ZIP은 전송용 압축이므로 풀고 EXE 하나만 전달하면 된다.

## 1차 전달 빌드

- 소스: `80779f204c9fe1a3f4f9eecb091405db51a772f9`
- [Windows CI 성공 기록](https://github.com/BapSangE/lol_live_widget/actions/runs/38840609609)
- 파일: `LoL-Live-Widget.exe`, 25,505,048 bytes
- SHA-256: `e58403c8641919958062c624e9facc21898b85252b5fa17762a9c706de0491b0`

후속 빌드는 파일 크기와 해시가 달라질 수 있다. 위 값은 사용자가 실행 확인한 첫 전달 파일의 식별값이다.
