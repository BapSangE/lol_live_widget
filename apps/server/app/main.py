from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.collectors.poller import Poller
from app.providers.lolesports import LoLEsportsProvider
from app.providers.replay import ReplayProvider
from app.storage.memory import MemoryStore


def create_app():
    @asynccontextmanager
    async def lifespan(app):
        mode = os.environ.get("SOURCE_MODE", "replay")
        if mode not in ("live", "replay"):
            raise ValueError("SOURCE_MODE must be live or replay")
        provider = (
            ReplayProvider(int(os.environ.get("REPLAY_STEP_SECONDS", "10")))
            if mode == "replay"
            else LoLEsportsProvider(
                os.environ.get("LOLESPORTS_API_KEY", ""),
                os.environ.get("SOURCE_APPROVED") == "true",
            )
        )
        store = MemoryStore(mode)
        poller = Poller(provider, store, float(os.environ.get("POLL_SECONDS", "10")))
        app.state.store, app.state.poller = store, poller
        await poller.tick()
        task = asyncio.create_task(poller.run())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            await provider.close()

    app = FastAPI(title="LoL Live Widget", version="0.1.0", lifespan=lifespan)
    origins = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://127.0.0.1:1420,http://localhost:1420,http://tauri.localhost,https://tauri.localhost,tauri://localhost",
    ).split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET"],
        allow_headers=["Last-Event-ID"],
        expose_headers=[],
    )
    app.include_router(router)
    return app


app = create_app()
