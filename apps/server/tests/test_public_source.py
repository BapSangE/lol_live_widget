import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import app.main as server_main
import httpx
import pytest
from app.collectors.poller import Poller
from app.providers import lolesports
from app.providers.base import AccessDenied
from app.storage.memory import MemoryStore
from fastapi.testclient import TestClient


def event(state="inProgress", game="g1", number=1):
    return {
        "__typename": "EventMatch",
        "id": "m",
        "state": state,
        "startTime": "2026-10-16T00:00:00Z",
        "league": {"slug": "worlds"},
        "matchTeams": [
            {
                "teamId": "kc",
                "code": "KC",
                "name": "Karmine Corp",
                "result": {"gameWins": 1},
            },
            {"teamId": "c9", "code": "C9", "name": "Cloud9", "result": {"gameWins": 0}},
        ],
        "match": {"games": [{"id": game, "state": state, "number": number}]},
    }


def page(*events):
    # The public page contains JS-only values outside the JSON event objects.
    return (
        '<script>(window[Symbol.for("ApolloSSRDataTransport")] ??= []).push({"loading":undefined,"events":'
        + json.dumps(events)
        + "})</script>"
    )


def source(client, approved=True):
    cls = getattr(lolesports, "PublicLoLEsportsProvider", None)
    assert cls is not None, "A keyless public schedule/feed provider is required"
    return cls(approved=approved, leagues=["worlds"], client=client)


@pytest.mark.asyncio
async def test_public_discovery_normalizes_team_ids_and_excludes_historical_matches():
    async def respond(request):
        if request.url.path == "/api/gql":
            return httpx.Response(200, json={"data": {"esports": {"events": []}}})
        assert "x-api-key" not in request.headers
        assert request.url.host == "lolesports.com"
        return httpx.Response(
            200, text=page(event(), event(), {**event("completed"), "id": "old"})
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        matches = await p.list_matches()
        assert len(matches) == 1
        assert (matches[0].blue.id, matches[0].red.id) == ("kc", "c9")
        assert (matches[0].game_id, matches[0].status) == ("g1", "live")
        assert (await p.health())["availability"] == "available"


@pytest.mark.asyncio
async def test_discovery_refreshes_active_game_and_keeps_terminal_match(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(lolesports.time, "monotonic", lambda: clock[0])
    current = [event()]

    async def respond(request):
        if request.url.path == "/api/gql":
            return httpx.Response(200, json={"data": {"esports": {"events": []}}})
        return httpx.Response(200, text=page(current[0]))

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        await p.list_matches()
        current[0] = event(game="g2", number=2)
        clock[0] += 11
        assert (await p.get_match("m")).game_id == "g2"
        current[0] = event("completed", "g2", 2)
        assert (await p.list_matches())[0].status == "ended"
        assert p.game_matches["g1"].game_id == "g1"


@pytest.mark.asyncio
async def test_live_windows_advance_and_reach_store_without_fabricating_game_clock(
    monkeypatch,
):
    now = datetime(2026, 10, 16, 0, 1, 40, tzinfo=UTC)
    monkeypatch.setattr(lolesports, "utcnow", lambda: now)
    starts = []

    async def respond(request):
        if request.url.path == "/api/gql":
            return httpx.Response(200, json={"data": {"esports": {"events": []}}})
        assert "x-api-key" not in request.headers
        if request.url.host == "lolesports.com":
            return httpx.Response(200, text=page(event()))
        if not request.url.params.get("startingTime"):
            return httpx.Response(200, json={"frames": []})
        stamp = request.url.params["startingTime"]
        starts.append(stamp)
        second = datetime.fromisoformat(stamp).second
        return httpx.Response(
            200,
            json={
                "gameMetadata": {
                    "blueTeamMetadata": {"esportsTeamId": "c9"},
                    "redTeamMetadata": {"esportsTeamId": "kc"},
                },
                "frames": [
                    {
                        "rfc460Timestamp": stamp,
                        "gameState": "in_game",
                        "blueTeam": {"totalKills": second // 10, "totalGold": 24000},
                        "redTeam": {"totalKills": 2, "totalGold": 25000},
                    }
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        m = (await p.list_matches())[0]
        frames = await p.get_game_frames(
            "g1", datetime(2026, 10, 16, 0, 0, 10, tzinfo=UTC)
        )
        assert starts == [
            "2026-10-16T00:00:10Z",
            "2026-10-16T00:00:20Z",
            "2026-10-16T00:00:30Z",
            "2026-10-16T00:00:40Z",
        ]
        assert frames[-1].game_time_seconds is None
        assert frames[-1].blue.id == "c9"
        store = MemoryStore("live")
        poller = Poller(p, store)
        await poller.collect(m)
        snapshot = await store.sync("m")
        assert snapshot.source_mode == "live"
        assert snapshot.state.blue.kills == 4
        assert snapshot.state.red.kills == 2
        assert any(e.type == "KILL_DELTA" for e in snapshot.events)


@pytest.mark.asyncio
@pytest.mark.parametrize("html", ["<html>maintenance</html>", page()])
async def test_changed_page_is_reported_as_source_failure_instead_of_empty_schedule(
    html,
):
    async def respond(request):
        if request.url.path == "/api/gql":
            return httpx.Response(200, json={"data": {"esports": {"events": []}}})
        return httpx.Response(200, text=html)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        with pytest.raises(ValueError):
            await p.list_matches()
        assert (await p.health())["availability"] == "source_unavailable"


@pytest.mark.asyncio
async def test_public_access_denial_stops_collector_without_exposing_credentials():
    async def respond(request):
        if request.url.path == "/api/gql":
            return httpx.Response(200, json={"data": {"esports": {"events": []}}})
        return httpx.Response(403)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        store = MemoryStore("live")
        poller = Poller(p, store)
        await poller.tick()
        assert poller.blocked
        assert store.source_error == "access_denied"


@pytest.mark.asyncio
async def test_public_mode_still_requires_explicit_opt_in():
    async with httpx.AsyncClient() as client:
        p = source(client, approved=False)
        with pytest.raises(AccessDenied):
            await p.list_matches()


@pytest.mark.asyncio
async def test_public_schedule_follows_real_website_redirects():
    async def respond(request):
        if request.url.path == "/api/gql":
            return httpx.Response(200, json={"data": {"esports": {"events": []}}})
        if request.url.path == "/en-US/schedule":
            return httpx.Response(308, headers={"location": "/en-US/leagues/worlds"})
        return httpx.Response(200, text=page(event()))

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        assert (await p.list_matches())[0].match_id == "m"


@pytest.mark.asyncio
async def test_completed_schedule_cannot_stop_before_terminal_feed_frame(monkeypatch):
    monkeypatch.setattr(
        lolesports, "utcnow", lambda: datetime(2026, 10, 16, 0, 1, 40, tzinfo=UTC)
    )
    state = ["inProgress"]

    async def respond(request):
        if request.url.path == "/api/gql":
            return httpx.Response(200, json={"data": {"esports": {"events": []}}})
        if request.url.host == "lolesports.com":
            return httpx.Response(200, text=page(event(state[0])))
        if not request.url.params.get("startingTime"):
            return httpx.Response(200, json={"frames": []})
        stamp = request.url.params["startingTime"]
        finished = stamp == "2026-10-16T00:00:40Z"
        return httpx.Response(
            200,
            json={
                "frames": [
                    {
                        "rfc460Timestamp": stamp,
                        "gameState": "finished" if finished else "in_game",
                        "blueTeam": {"totalKills": 4 if finished else 3},
                        "redTeam": {"totalKills": 2},
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        await p.list_matches()
        state[0] = "completed"
        match = (await p.list_matches())[0]
        store = MemoryStore("live")
        poller = Poller(p, store)
        assert await poller.collect(match) is True
        snapshot = await store.sync("m")
        assert snapshot.state.blue.kills == 4
        assert snapshot.state.source_timestamp == datetime(
            2026, 10, 16, 0, 0, 40, tzinfo=UTC
        )
        assert any(e.type == "KILL_DELTA" for e in snapshot.events)


@pytest.mark.asyncio
async def test_schedule_rate_limit_is_not_retried_by_each_active_match(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(lolesports.time, "monotonic", lambda: clock[0])
    requests = []
    rejected = [False]

    async def respond(request):
        if request.url.path == "/api/gql":
            return httpx.Response(200, json={"data": {"esports": {"events": []}}})
        requests.append(request.url)
        return (
            httpx.Response(429)
            if rejected[0]
            else httpx.Response(200, text=page(event()))
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        await p.list_matches()
        rejected[0] = True
        clock[0] += 11
        with pytest.raises(httpx.HTTPStatusError):
            await p.list_matches()
        assert (await p.get_match("m")).game_id == "g1"
        assert len(requests) == 2


@pytest.mark.asyncio
async def test_empty_feed_gap_does_not_permanently_trap_scan_cursor(monkeypatch):
    monkeypatch.setattr(
        lolesports, "utcnow", lambda: datetime(2026, 10, 16, 0, 5, tzinfo=UTC)
    )

    async def respond(request):
        if request.url.path == "/api/gql":
            return httpx.Response(200, json={"data": {"esports": {"events": []}}})
        if request.url.host == "lolesports.com":
            return httpx.Response(200, text=page(event()))
        if not request.url.params.get("startingTime"):
            return httpx.Response(200, json={"frames": []})
        stamp = request.url.params["startingTime"]
        resumed = datetime.fromisoformat(stamp) >= datetime(
            2026, 10, 16, 0, 2, tzinfo=UTC
        )
        return httpx.Response(
            200,
            json={
                "frames": [
                    {
                        "rfc460Timestamp": stamp,
                        "gameState": "in_game",
                        "blueTeam": {"totalKills": 7},
                        "redTeam": {"totalKills": 4},
                    }
                ]
                if resumed
                else []
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        await p.list_matches()
        old = datetime(2026, 10, 16, 0, 0, 20, tzinfo=UTC)
        assert await p.get_game_frames("g1", old) == []
        recovered = []
        for _ in range(3):
            recovered.extend(await p.get_game_frames("g1", old))
        assert recovered
        assert recovered[-1].blue.kills == 7


def test_public_mode_bootstraps_rest_without_api_key(monkeypatch):
    monkeypatch.setenv("SOURCE_MODE", "live")
    monkeypatch.setenv("SOURCE_APPROVED", "true")
    monkeypatch.setenv("LIVE_PROVIDER", "public")
    monkeypatch.setenv("LIVE_LEAGUES", "worlds")
    monkeypatch.delenv("LOLESPORTS_API_KEY", raising=False)
    monkeypatch.setattr(
        lolesports, "utcnow", lambda: datetime(2026, 10, 16, 0, 1, 40, tzinfo=UTC)
    )

    async def respond(request):
        if request.url.path == "/api/gql":
            return httpx.Response(200, json={"data": {"esports": {"events": []}}})
        assert "x-api-key" not in request.headers
        if request.url.host == "lolesports.com":
            return httpx.Response(200, text=page(event()))
        if not request.url.params.get("startingTime"):
            return httpx.Response(200, json={"frames": []})
        stamp = request.url.params["startingTime"]
        return httpx.Response(
            200,
            json={
                "frames": [
                    {
                        "rfc460Timestamp": stamp,
                        "gameState": "in_game",
                        "blueTeam": {"totalKills": 4 if ":40Z" in stamp else 3},
                        "redTeam": {"totalKills": 2},
                    }
                ]
            },
        )

    def provider(**kwargs):
        return lolesports.PublicLoLEsportsProvider(
            **kwargs, client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
        )

    monkeypatch.setattr(server_main, "PublicLoLEsportsProvider", provider)
    with TestClient(server_main.create_app()) as client:
        assert client.get("/api/v1/health").json()["sourceStatus"] == "available"
        assert client.get("/api/v1/matches?league=worlds").json()[0]["matchId"] == "m"
        snap = client.get("/api/v1/matches/m/sync").json()
        assert snap["sourceMode"] == "live"
        assert snap["state"]["blue"]["kills"] == 4
        assert snap["events"][0]["type"] == "KILL_DELTA"
        assert (
            client.get("/api/v1/matches/m/events").json()["items"][0]["id"]
            == snap["events"][0]["id"]
        )


@pytest.mark.asyncio
async def test_live_match_missing_from_html_reaches_store_and_refreshes_next_game(
    monkeypatch,
):
    payload = json.loads(
        (
            Path(__file__).resolve().parents[3]
            / "fixtures/captures/worlds-2026-11-04-tes-ig-live.json"
        ).read_text()
    )
    clock = [100.0]
    monkeypatch.setattr(lolesports.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        lolesports, "utcnow", lambda: datetime(2026, 11, 4, 0, 30, tzinfo=UTC)
    )
    stale = {**payload["data"]["esports"]["events"][0], "state": "unstarted"}
    stale["match"] = {"games": []}
    schedule = [event("unstarted")]

    async def respond(request):
        if request.url.path == "/api/gql":
            assert request.method == "GET"
            assert "x-api-key" not in request.headers
            assert request.headers["content-type"] == "application/json"
            assert request.headers["apollographql-client-name"]
            assert json.loads(request.url.params["variables"])["eventState"] == [
                "inProgress"
            ]
            return httpx.Response(200, json=payload)
        if request.url.host == "lolesports.com":
            return httpx.Response(200, text=page(*schedule))
        if not request.url.params.get("startingTime"):
            return httpx.Response(200, json={"frames": []})
        return httpx.Response(
            200,
            json={
                "gameMetadata": {
                    "blueTeamMetadata": {"esportsTeamId": "99566404854685458"},
                    "redTeamMetadata": {"esportsTeamId": "99566404848691211"},
                },
                "frames": [
                    {
                        "rfc460Timestamp": request.url.params["startingTime"],
                        "gameState": "in_game",
                        "blueTeam": {"totalKills": 7},
                        "redTeam": {"totalKills": 4},
                    }
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        match = (await p.list_matches())[0]
        assert (match.match_id, match.status, match.game_id, match.game_number) == (
            "115660540726095109",
            "live",
            "115660540726095112",
            3,
        )
        poller = Poller(p, MemoryStore("live"))
        await poller.collect(match)
        snap = await poller.store.sync(match.match_id)
        assert (snap.state.blue.short_name, snap.state.blue.kills) == ("TES", 7)
        assert (snap.state.red.short_name, snap.state.red.kills) == ("IG", 4)
        schedule.append(stale)
        games = payload["data"]["esports"]["events"][0]["match"]["games"]
        games[2]["state"], games[3]["state"] = "completed", "inProgress"
        clock[0] += 11
        refreshed = await p.get_match(match.match_id)
        assert (refreshed.game_id, refreshed.game_number, refreshed.status) == (
            "115660540726095113",
            4,
            "live",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"errors": [{"message": "query changed"}]},
        {"data": {"esports": None}},
        {"data": {"esports": {"events": {}}}},
    ],
)
async def test_live_query_failure_is_not_reported_as_healthy_empty_schedule(payload):
    async def respond(request):
        if request.url.path == "/api/gql":
            return httpx.Response(200, json=payload)
        return httpx.Response(200, text=page(event("unstarted")))

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        poller = Poller(p, MemoryStore("live"))
        await poller.tick()
        assert poller.store.source_error == "source_unavailable"
        assert (await p.health())["availability"] == "source_unavailable"


@pytest.mark.asyncio
async def test_live_windows_respect_feed_fifty_second_broadcast_delay(monkeypatch):
    now = datetime(2026, 11, 4, 0, 34, 7, tzinfo=UTC)
    monkeypatch.setattr(lolesports, "utcnow", lambda: now)

    async def respond(request):
        if request.url.path == "/api/gql":
            return httpx.Response(200, json={"data": {"esports": {"events": []}}})
        if request.url.host == "lolesports.com":
            return httpx.Response(200, text=page(event()))
        if not request.url.params.get("startingTime"):
            return httpx.Response(200, json={"frames": []})
        start = datetime.fromisoformat(request.url.params["startingTime"])
        if start + timedelta(seconds=10) > now - timedelta(seconds=50):
            return httpx.Response(400, json={"message": "window ahead of broadcast"})
        return httpx.Response(
            200,
            json={
                "frames": [
                    {
                        "rfc460Timestamp": start.isoformat(),
                        "gameState": "in_game",
                        "blueTeam": {"totalKills": 4},
                        "redTeam": {"totalKills": 2},
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        await p.list_matches()
        frames = await p.get_game_frames("g1")
        assert frames[-1].blue.kills == 4
        assert frames[-1].source_timestamp == datetime(2026, 11, 4, 0, 33, tzinfo=UTC)


@pytest.mark.asyncio
async def test_new_game_without_published_frames_waits_without_source_error(
    monkeypatch,
):
    monkeypatch.setattr(
        lolesports, "utcnow", lambda: datetime(2026, 11, 4, 0, 54, tzinfo=UTC)
    )

    async def respond(request):
        if request.url.path == "/api/gql":
            return httpx.Response(200, json={"data": {"esports": {"events": []}}})
        if request.url.host == "lolesports.com":
            return httpx.Response(200, text=page(event(game="new-game", number=4)))
        return httpx.Response(204)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        poller = Poller(p, MemoryStore("live"))
        await poller.tick()
        assert poller.matches[0].game_number == 4
        assert poller.store.source_error is None
        assert (await p.health())["availability"] == "available"


def test_player_normalization_requires_source_names_and_preserves_missing_counters():
    metadata = {
        "participantMetadata": [
            {"participantId": 1, "summonerName": "T1 Zeus"},
            {"participantId": 2, "summonerName": " "},
        ]
    }
    players = lolesports.LoLEsportsProvider._players(
        {
            "participants": [
                {"participantId": 1, "kills": True, "deaths": -1},
                {"participantId": 2, "kills": 1, "deaths": 0},
                {"participantId": 3, "kills": 1, "deaths": 0},
            ]
        },
        metadata,
        "t1",
    )
    assert len(players) == 1
    assert players[0].name == "T1 Zeus"
    assert players[0].kills is None and players[0].deaths is None


@pytest.mark.asyncio
async def test_estimated_clock_uses_first_feed_frame_when_joining_midgame_and_resets_per_set(
    monkeypatch,
):
    monkeypatch.setattr(
        lolesports, "utcnow", lambda: datetime(2026, 11, 9, 0, 11, tzinfo=UTC)
    )
    bootstraps = []

    async def respond(request):
        game_id = request.url.path.rsplit("/", 1)[-1]
        stamp = request.url.params.get("startingTime")
        if not stamp:
            bootstraps.append(game_id)
            stamp = (
                "2026-11-09T00:00:00Z" if game_id == "g1" else "2026-11-09T00:05:00Z"
            )
        return httpx.Response(
            200,
            json={
                "frames": [
                    {
                        "rfc460Timestamp": stamp,
                        "gameState": "in_game",
                        "blueTeam": {"totalKills": 1},
                        "redTeam": {"totalKills": 0},
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        summary = p._summary(
            {
                "id": "m",
                "state": "inProgress",
                "match": {
                    "teams": [{"id": "b", "name": "Blue"}, {"id": "r", "name": "Red"}]
                },
            }
        )
        p.game_matches.update({"g1": summary, "g2": summary})
        frames = await p.get_game_frames("g1")
        assert frames[-1].game_time_seconds is None
        assert frames[-1].model_dump().get("estimated_game_time_seconds") == 600
        await p.get_game_frames("g1")
        next_set = await p.get_game_frames("g2")
        assert next_set[-1].model_dump().get("estimated_game_time_seconds") == 300
        assert bootstraps == ["g1", "g2"]
        p.game_starts["g1"] = datetime(2026, 11, 9, tzinfo=UTC)
        exact = p._frames(
            {
                "frames": [
                    {"rfc460Timestamp": "2026-11-09T00:10:00Z", "gameTimeSeconds": 123}
                ]
            },
            "g1",
        )[0]
        assert exact.game_time_seconds == 123
        assert exact.estimated_game_time_seconds is None


@pytest.mark.asyncio
@pytest.mark.parametrize("bootstrap_status", [400, 500, None])
async def test_optional_clock_failure_does_not_block_current_statistics(
    monkeypatch, bootstrap_status
):
    monkeypatch.setattr(
        lolesports, "utcnow", lambda: datetime(2026, 11, 9, 0, 11, tzinfo=UTC)
    )

    async def respond(request):
        stamp = request.url.params.get("startingTime")
        if not stamp:
            if bootstrap_status is not None:
                return httpx.Response(bootstrap_status)
            return httpx.Response(
                200, json={"frames": [{"rfc460Timestamp": "invalid"}]}
            )
        return httpx.Response(
            200,
            json={
                "frames": [{"rfc460Timestamp": stamp, "blueTeam": {"totalKills": 3}}]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        p.game_matches["g1"] = p._summary(
            {
                "id": "m",
                "state": "inProgress",
                "match": {"teams": [{"id": "b"}, {"id": "r"}]},
            }
        )
        frames = await p.get_game_frames("g1")
        assert frames[-1].blue.kills == 3
        assert frames[-1].estimated_game_time_seconds is None
        assert (await p.health())["availability"] == "available"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [403, 429])
async def test_optional_clock_still_respects_access_denial_and_rate_limits(status):
    async def respond(request):
        return httpx.Response(status)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        p = source(client)
        with pytest.raises(AccessDenied if status == 403 else httpx.HTTPStatusError):
            await p.get_game_frames("g1")
