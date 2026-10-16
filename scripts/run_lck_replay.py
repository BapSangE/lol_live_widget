"""Run the downloaded LCK sample with the local server and widget preview."""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(*, live: bool = False, league: str = "worlds") -> None:
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
    env = dict(os.environ, VITE_SERVER_URL="http://127.0.0.1:8000")
    if live:
        env.update(
            SOURCE_MODE="live",
            SOURCE_APPROVED="true",
            LIVE_PROVIDER="public",
            LIVE_LEAGUES=league,
            VITE_LEAGUE=league,
            POLL_SECONDS="10",
        )
        env.pop("REPLAY_FIXTURE", None)
    else:
        env.update(
            SOURCE_MODE="replay",
            POLL_SECONDS="1",
            VITE_LEAGUE="lck",
            REPLAY_FIXTURE="fixtures/captures/lck-2026-09-13-gen-hle-game1/frames.json",
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
        description = (
            f"Live {league}: http://127.0.0.1:1420 — public schedule/feed, no API key. Waiting if no match is live."
            if live
            else "Starting LCK archive: http://127.0.0.1:1420 — 69-second sample. Ctrl+C stops both; run again to replay."
        )
        print(description, flush=True)
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
