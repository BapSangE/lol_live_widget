"""Run the downloaded LCK sample with the local server and widget preview."""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    node = ROOT / ".tools/node-v22.23.3-darwin-arm64/bin/node"
    node = str(node) if node.exists() else shutil.which("node")
    if not node:
        raise SystemExit("Node.js is required. See README.md.")
    for port in (8000, 1420):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit(
                    f"Port {port} is in use. Stop the previous preview (Ctrl+C) first."
                )
    env = dict(
        os.environ,
        SOURCE_MODE="replay",
        POLL_SECONDS="1",
        REPLAY_FIXTURE="fixtures/captures/lck-2026-09-13-gen-hle-game1/frames.json",
        VITE_SERVER_URL="http://127.0.0.1:8000",
        VITE_LEAGUE="lck",
    )
    processes = []
    try:
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--app-dir",
                    "apps/server",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                cwd=ROOT,
                env=env,
            )
        )
        processes.append(
            subprocess.Popen(
                [
                    node,
                    str(ROOT / "apps/desktop/node_modules/vite/bin/vite.js"),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "1420",
                    "--strictPort",
                ],
                cwd=ROOT / "apps/desktop",
                env=env,
            )
        )
        print(
            "Starting LCK archive: http://127.0.0.1:1420 — 69-second sample. Ctrl+C stops both; run again to replay.",
            flush=True,
        )
        while all(p.poll() is None for p in processes):
            time.sleep(0.5)
        raise SystemExit("Preview process stopped unexpectedly; see the error above.")
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
