"""Single-file Windows launcher: own one local collector and one Tauri widget."""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import uvicorn

log = logging.getLogger(__name__)


def bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


class EmbeddedServer:
    def __init__(self, *, demo: bool = False, league: str = "worlds") -> None:
        self.demo, self.league = demo, league
        self.origin = ""
        self.socket = None
        self.thread = None
        self.server = None
        self.error = None
        self.previous = {}

    def __enter__(self):
        configuration = {
            "SOURCE_MODE": "replay" if self.demo else "live",
            "SOURCE_APPROVED": "true",
            "LIVE_PROVIDER": "public",
            "LIVE_LEAGUES": self.league,
            "POLL_SECONDS": "10",
            "REPLAY_FIXTURE": None,
        }
        for name, value in configuration.items():
            self.previous[name] = os.environ.get(name)
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        try:
            from app.main import create_app

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(("127.0.0.1", 0))
            self.socket.listen(128)
            self.origin = f"http://127.0.0.1:{self.socket.getsockname()[1]}"
            self.server = uvicorn.Server(
                uvicorn.Config(
                    create_app(),
                    host="127.0.0.1",
                    log_config=None,
                    access_log=False,
                    loop="asyncio",
                    http="h11",
                    ws="none",
                    timeout_graceful_shutdown=2,
                )
            )

            def serve():
                try:
                    self.server.run(sockets=[self.socket])
                except BaseException as error:
                    self.error = error
                    log.exception("Collector stopped")

            self.thread = threading.Thread(target=serve, daemon=True, name="collector")
            self.thread.start()
            deadline = time.monotonic() + 30
            while not self.server.started:
                if self.error or not self.thread.is_alive():
                    raise RuntimeError("Collector could not start") from self.error
                if time.monotonic() >= deadline:
                    raise TimeoutError("Collector startup timed out")
                time.sleep(0.05)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        if self.server:
            self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout=5)
        if self.socket:
            self.socket.close()
        for name, value in self.previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def has_webview() -> bool:
    if sys.platform != "win32":
        return True
    import winreg

    client = r"Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    for hive, prefix in (
        (winreg.HKEY_CURRENT_USER, "SOFTWARE\\"),
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\"),
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\"),
    ):
        try:
            with winreg.OpenKey(hive, prefix + client) as key:
                version = winreg.QueryValueEx(key, "pv")[0]
                if version and version != "0.0.0.0":
                    return True
        except OSError:
            continue
    return False


def ensure_webview() -> None:
    if has_webview():
        return
    import ctypes

    answer = ctypes.windll.user32.MessageBoxW(
        None,
        "위젯 실행에 필요한 Microsoft WebView2를 설치할까요? 인터넷 연결이 필요합니다.",
        "LoL Live Widget",
        0x04 | 0x20,
    )
    if answer != 6:
        raise RuntimeError("WebView2 installation was cancelled")
    installer = bundle_root() / "webview" / "MicrosoftEdgeWebview2Setup.exe"
    result = subprocess.run(
        [str(installer), "/silent", "/install"],
        timeout=300,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    if result.returncode != 0 or not has_webview():
        raise RuntimeError("Microsoft WebView2 could not be installed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Use offline demo data")
    parser.add_argument("--league", default="worlds", choices=["worlds", "lck"])
    parser.add_argument(
        "--smoke-test", action="store_true", help="Check the bundled collector and exit"
    )
    args = parser.parse_args()
    logs = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LoLLiveWidget"
    logs.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=logs / "portable.log", level=logging.INFO)
    child = None
    try:
        if not args.smoke_test:
            ensure_webview()
        with EmbeddedServer(
            demo=args.demo or args.smoke_test, league=args.league
        ) as server:
            if args.smoke_test:
                health = httpx.get(server.origin + "/api/v1/health", timeout=5).json()
                matches = httpx.get(server.origin + "/api/v1/matches", timeout=5).json()
                if health["sourceMode"] != "replay" or not matches:
                    raise RuntimeError("Bundled collector smoke test failed")
                (logs / "portable-smoke.json").write_text(
                    json.dumps({"ok": True, "health": health})
                )
                return 0
            ui = bundle_root() / "desktop" / "lol-live-widget.exe"
            if not ui.is_file():
                raise FileNotFoundError("Bundled desktop widget is missing")
            env = dict(
                os.environ,
                LOL_WIDGET_LOCAL_SERVER_URL=server.origin,
                LOL_WIDGET_LAUNCHER_PATH=str(Path(sys.executable).resolve()),
            )
            child = subprocess.Popen([str(ui)], env=env)
            while child.poll() is None:
                if not server.thread.is_alive():
                    raise RuntimeError("Local collector stopped unexpectedly")
                time.sleep(0.25)
            return child.returncode
    except Exception as error:
        log.exception("Portable widget failed")
        if sys.platform == "win32" and not args.smoke_test:
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                None,
                f"위젯을 실행할 수 없습니다.\n{error}\n\n로그: {logs / 'portable.log'}",
                "LoL Live Widget",
                0x10,
            )
        return 1
    finally:
        if child and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
