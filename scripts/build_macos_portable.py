"""Build a self-contained Apple Silicon macOS app and DMG."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "apps/desktop"
TAURI = DESKTOP / "src-tauri"
PYTHON = ROOT / ".venv312/bin/python"
NODE = shutil.which("node")


def run(
    command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None
) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-packaged-smoke-test", action="store_true")
    parser.add_argument("--reuse-sidecar", action="store_true")
    args = parser.parse_args()
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise SystemExit("Run this build on an Apple Silicon Mac (arm64).")
    if not PYTHON.is_file():
        raise SystemExit("Create .venv312 and install apps/server[test] first.")
    if not NODE:
        raise SystemExit("Node.js is required on the build host.")

    work = ROOT / "build/macos"
    dist = ROOT / "dist/macos"
    work.mkdir(parents=True, exist_ok=True)
    dist.mkdir(parents=True, exist_ok=True)
    sidecar = dist / "LoL-Live-Widget-Server"
    pyinstaller = [
        str(PYTHON),
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--console",
        "--name",
        sidecar.name,
        "--paths",
        str(ROOT / "apps/server"),
        "--workpath",
        str(work / "pyinstaller"),
        "--specpath",
        str(work),
        "--distpath",
        str(dist),
        "--add-data",
        f"{ROOT / 'fixtures/raw_frames'}:fixtures/raw_frames",
    ]
    for package in (
        "uvicorn",
        "fastapi",
        "starlette",
        "pydantic",
        "pydantic_core",
        "anyio",
        "certifi",
    ):
        pyinstaller.extend(["--collect-all", package])
    pyinstaller.append(str(ROOT / "scripts/portable_launcher.py"))
    build_env = dict(
        os.environ, PYINSTALLER_CONFIG_DIR=str(work / "pyinstaller-config")
    )
    if args.reuse_sidecar and not sidecar.is_file():
        raise SystemExit(f"Cannot reuse missing sidecar: {sidecar}")
    if not args.reuse_sidecar:
        run(pyinstaller, env=build_env)
    if not args.skip_packaged_smoke_test:
        run(
            [str(sidecar), "--smoke-test"],
            env=dict(build_env, LOL_WIDGET_LOG_DIR=str(work / "smoke-logs")),
        )

    icon_source = work / "icon.png"
    run(
        [
            "sips",
            "-s",
            "format",
            "png",
            str(TAURI / "icons/icon.ico"),
            "--out",
            str(icon_source),
        ]
    )
    generated_icons = work / "icons"
    run(
        [
            NODE,
            "node_modules/@tauri-apps/cli/tauri.js",
            "icon",
            str(icon_source),
            "--output",
            str(generated_icons),
        ],
        cwd=DESKTOP,
    )
    shutil.copy2(generated_icons / "icon.icns", TAURI / "icons/icon.icns")

    env = dict(
        os.environ, VITE_PORTABLE="true", VITE_SERVER_URL="", VITE_LEAGUE="worlds"
    )
    run(
        [
            NODE,
            "scripts/tauri.mjs",
            "build",
            "--features",
            "macos-portable",
            "--target",
            "aarch64-apple-darwin",
            "--bundles",
            "app,dmg",
            "--no-sign",
            "--config",
            "src-tauri/tauri.macos-portable.conf.json",
        ],
        cwd=DESKTOP,
        env=env,
    )
    print(
        f"DMG: {TAURI / 'target/aarch64-apple-darwin/release/bundle/dmg'}", flush=True
    )


if __name__ == "__main__":
    main()
