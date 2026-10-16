"""Build the one-file Windows x64 widget on a Windows build host."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != "win32":
        raise SystemExit(
            "This build must run on Windows (or GitHub Actions windows-latest)."
        )
    node = shutil.which("node")
    if not node:
        raise SystemExit("Node.js is required on the build host.")
    work = ROOT / "build" / "portable"
    work.mkdir(parents=True, exist_ok=True)
    bootstrapper = work / "MicrosoftEdgeWebview2Setup.exe"
    response = httpx.get(
        "https://go.microsoft.com/fwlink/p/?LinkId=2124703",
        follow_redirects=True,
        timeout=60,
    )
    response.raise_for_status()
    bootstrapper.write_bytes(response.content)
    signature_script = work / "verify-signature.ps1"
    signature_script.write_text(
        "param([string]$Installer)\n"
        "$s=Get-AuthenticodeSignature -LiteralPath $Installer\n"
        "if ($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notlike '*Microsoft Corporation*') {exit 1}\n"
    )
    signature = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(signature_script),
            "-Installer",
            str(bootstrapper),
        ],
        check=False,
    )
    if signature.returncode:
        raise SystemExit(
            "WebView2 bootstrapper does not have a valid Microsoft signature."
        )
    env = dict(
        os.environ, VITE_PORTABLE="true", VITE_SERVER_URL="", VITE_LEAGUE="worlds"
    )
    env["RUSTFLAGS"] = (
        env.get("RUSTFLAGS", "") + " -C target-feature=+crt-static"
    ).strip()
    subprocess.run(
        [node, "scripts/tauri.mjs", "build", "--no-bundle"],
        cwd=ROOT / "apps/desktop",
        env=env,
        check=True,
    )
    ui = ROOT / "apps/desktop/src-tauri/target/release/lol-live-widget.exe"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "LoL-Live-Widget",
        "--paths",
        str(ROOT / "apps/server"),
        "--workpath",
        str(work / "pyinstaller"),
        "--specpath",
        str(work),
        "--distpath",
        str(ROOT / "dist"),
        "--icon",
        str(ROOT / "apps/desktop/src-tauri/icons/icon.ico"),
        "--add-binary",
        f"{ui};desktop",
        "--add-binary",
        f"{bootstrapper};webview",
        "--add-data",
        f"{ROOT / 'fixtures/raw_frames'};fixtures/raw_frames",
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
        command.extend(["--collect-all", package])
    command.append(str(ROOT / "scripts/portable_launcher.py"))
    subprocess.run(command, cwd=ROOT, check=True)
    print(f"Portable executable: {ROOT / 'dist/LoL-Live-Widget.exe'}", flush=True)


if __name__ == "__main__":
    main()
