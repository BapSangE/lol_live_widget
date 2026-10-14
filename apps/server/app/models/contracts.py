from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

EventType = Literal[
    "KILL_DELTA",
    "MULTIKILL_WINDOW",
    "DRAGON",
    "BARON",
    "ELDER",
    "DRAGON_SOUL",
    "TOWER",
    "GOLD_LEAD_CHANGE",
    "GAME_END",
]
MatchStatus = Literal["scheduled", "live", "ended", "unknown"]


def utcnow() -> datetime:
    return datetime.now(UTC)


class Contract(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", frozen=True
    )


class TeamState(Contract):
    id: str
    name: str
    short_name: str
    series_wins: int = Field(default=0, ge=0)
    kills: int | None = Field(default=None, ge=0)
    gold: int | None = Field(default=None, ge=0)
    towers: int | None = Field(default=None, ge=0, le=11)
    dragons: int | None = Field(default=None, ge=0)
    barons: int | None = Field(default=None, ge=0)


class MatchSummary(Contract):
    match_id: str
    league: str = "worlds"
    status: MatchStatus = "live"
    blue: TeamState
    red: TeamState
    game_id: str | None = None
    game_number: int | None = None
    scheduled_at: datetime | None = None


class RawFrame(Contract):
    match_id: str
    game_id: str = Field(min_length=1)
    source_timestamp: datetime
    game_time_seconds: int | None = Field(default=None, ge=0)
    blue: TeamState
    red: TeamState
    status: MatchStatus = "live"
    league: str = "worlds"
    game_number: int | None = 1
    winner_team_id: str | None = None
    elder_team_id: str | None = None
    soul_team_id: str | None = None

    @field_validator("source_timestamp")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("source timestamp must include timezone")
        return value.astimezone(UTC)


class MatchState(Contract):
    match_id: str
    game_id: str | None
    status: MatchStatus
    connection: Literal["live", "delayed", "offline"]
    league: str
    blue: TeamState
    red: TeamState
    game_number: int | None
    game_time_seconds: int | None
    source_timestamp: datetime | None
    received_at: datetime
    revision: int = Field(ge=0)
    source_error: str | None = None


class MatchEvent(Contract):
    id: str
    match_id: str
    game_id: str
    type: EventType
    game_time_seconds: int | None
    occurred_at: datetime | None
    observed_at: datetime
    team_id: str | None
    priority: Literal["normal", "important", "critical"]
    message_ko: str
    confidence: Literal["confirmed", "derived"]
    source_revision: int


class SyncSnapshot(Contract):
    state: MatchState
    events: list[MatchEvent]
    stream_cursor: str
    source_mode: Literal["live", "replay"]


class EventsPage(Contract):
    items: list[MatchEvent]
    next_cursor: str | None
