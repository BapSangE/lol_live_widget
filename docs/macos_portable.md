# macOS 무설치 앱

[macOS Apple Silicon DMG 다운로드](https://github.com/BapSangE/lol_live_widget/releases/latest/download/LoL-Live-Widget-macOS-arm64.dmg) · [릴리스 안내](https://github.com/BapSangE/lol_live_widget/releases/latest)

Apple Silicon(arm64)에서 `LoL Live Widget.app`과 전달용 단일 DMG를 빌드합니다. 앱 번들 안에 공개 피드 수집기가 들어 있어 Python, Node.js, Rust, 별도 API 키 없이 실행됩니다. 앱이 닫히면 수집기도 함께 종료됩니다.

사용자 Mac에서 앱 실행을 확인했습니다. 실제 진행 중 경기의 연속 수신·세트 전환은 추가 검증 대상입니다.

## 빌드

macOS arm64에서 Node.js 22, Python 3.12, Rust stable, Xcode Command Line Tools가 필요합니다. 저장소 루트에서:

```sh
npm --prefix apps/desktop ci
python3.12 -m venv .venv312
.venv312/bin/python -m pip install -e 'apps/server[test]' 'pyinstaller>=6.10,<7'
.venv312/bin/python scripts/build_macos_portable.py
```

산출물은 `apps/desktop/src-tauri/target/aarch64-apple-darwin/release/bundle/dmg/`의 `.dmg` 하나입니다. DMG를 열고 앱을 Applications 폴더로 옮겨 실행합니다.

## 첫 실행 경고

현재 빌드는 코드 서명과 Apple 공증 없이 생성됩니다. macOS가 확인되지 않은 개발자 경고를 표시하면 Finder에서 앱을 우클릭해 **열기**를 선택하고 한 번 더 확인합니다. macOS 버전에 따라 **시스템 설정 → 개인정보 보호 및 보안 → 확인 없이 열기**에서 허용해야 할 수 있습니다. 이 경고를 허용하지 않는 환경에서는 실행할 수 없습니다. 서명·공증된 배포본을 만들려면 Developer ID와 Apple 공증 설정이 별도로 필요합니다.

## 동작과 진단

- 공개 Worlds 라이브 피드를 사용하며 인터넷 연결이 필요합니다. 수집기는 앱 실행 중에만 동작합니다.
- 로그: `~/Library/Logs/LoLLiveWidget/portable.log`
- 설정: `~/Library/Application Support/com.lollive.widget/`
- 앱은 Apple Silicon용입니다. Intel Mac용은 별도 빌드가 필요합니다.
- `.dmg`는 설치 이미지이며 앱 바이너리 자체를 단일 파일로 합친 구조는 아닙니다. 사용자는 DMG 안에서 앱을 Applications로 복사해 사용합니다.
