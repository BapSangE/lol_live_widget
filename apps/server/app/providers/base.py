from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.models.contracts import MatchSummary, RawFrame


class Provider(Protocol):
    async def list_matches(self) -> list[MatchSummary]: ...
    async def get_match(self, match_id: str) -> MatchSummary: ...
    async def get_game_frames(
        self, game_id: str, after_source_timestamp: datetime | None
    ) -> list[RawFrame]: ...
    async def get_game_details(
        self, game_id: str, timestamp: datetime
    ) -> dict | None: ...
    async def health(self) -> dict: ...
    async def close(self) -> None: ...


class AccessDenied(Exception):
    pass
