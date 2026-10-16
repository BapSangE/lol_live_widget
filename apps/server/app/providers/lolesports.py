from __future__ import annotations

import json
import re
import time
from datetime import timedelta

import httpx

from app.models.contracts import MatchSummary, RawFrame, TeamState, utcnow
from app.providers.base import AccessDenied


class LoLEsportsProvider:
    """Opt-in unofficial adapter; credentials never enter client or repository."""

    def __init__(
        self, key: str, approved: bool, client: httpx.AsyncClient | None = None
    ):
        self.key = key
        self.approved = approved
        self.client = client or httpx.AsyncClient(timeout=5)
        self.matches = {}
        self.game_matches = {}
        self.latency = 0
        self.errors = 0
        self.last_error = None

    async def _request(self, path, params=None, feed=False):
        if not self.approved or not self.key:
            self.last_error = "access_denied"
            raise AccessDenied(
                "Live source requires documented approval and server credentials"
            )
        base = (
            "https://feed.lolesports.com/livestats/v1"
            if feed
            else "https://esports-api.lolesports.com/persisted/gw"
        )
        started = time.monotonic()
        try:
            response = await self.client.get(
                f"{base}/{path}", params=params, headers={"x-api-key": self.key}
            )
            if response.status_code in (401, 403):
                raise AccessDenied("Source rejected access")
            response.raise_for_status()
            result = response.json()
            self.last_error = None
            return result
        except (httpx.HTTPError, ValueError, AccessDenied):
            self.errors += 1
            raise
        finally:
            self.latency = round((time.monotonic() - started) * 1000)

    @staticmethod
    def _summary(event):
        match = event.get("match", {})
        teams = match.get("teams", [])
        if len(teams) != 2:
            return None

        def team(t):
            return TeamState(
                id=str(t["id"]),
                name=t.get("name", str(t["id"])),
                short_name=t.get("code") or t.get("name", str(t["id"]))[:6],
                series_wins=(t.get("result") or {}).get("gameWins", 0),
            )

        status = {
            "inProgress": "live",
            "completed": "ended",
            "unstarted": "scheduled",
        }.get(event.get("state"), "unknown")
        games = match.get("games", [])
        game = next((g for g in games if g.get("state") == "inProgress"), None)
        if game is None:
            game = next(
                (g for g in reversed(games) if g.get("state") == "completed"), None
            )
        return MatchSummary(
            match_id=str(event["id"]),
            league="worlds"
            if "world"
            in (
                event.get("league", {}).get("slug", "")
                + event.get("league", {}).get("name", "")
            ).lower()
            else event.get("league", {}).get("slug", "unknown"),
            status=status,
            blue=team(teams[0]),
            red=team(teams[1]),
            game_id=str(game["id"]) if game else None,
            game_number=game.get("number") if game else None,
            scheduled_at=event.get("startTime"),
        )

    async def list_matches(self):
        live = await self._request("getLive", {"hl": "en-US"})
        schedule = await self._request("getSchedule", {"hl": "en-US"})
        raw = live.get("data", {}).get("schedule", {}).get("events", []) + schedule.get(
            "data", {}
        ).get("schedule", {}).get("events", [])
        result = {}
        for event in raw:
            if event.get("type") not in (None, "match"):
                continue
            summary = self._summary(event)
            if summary and summary.league == "worlds":
                result.setdefault(summary.match_id, summary)
        self.matches = result
        for m in result.values():
            if m.game_id:
                self.game_matches[m.game_id] = m
        return list(result.values())

    async def get_match(self, match_id):
        payload = await self._request(
            "getEventDetails", {"hl": "en-US", "id": match_id}
        )
        event = payload.get("data", {}).get("event")
        summary = self._summary(event or {})
        if summary is None:
            raise ValueError("Unsupported match details")
        self.matches[match_id] = summary
        if summary.game_id:
            self.game_matches[summary.game_id] = summary
        return summary

    @staticmethod
    def _stats(raw, team):
        participants = raw.get("participants", [])

        def number(field, participant_field=None):
            value = raw.get(field)
            if (
                value is None
                and participants
                and participant_field
                and all(p.get(participant_field) is not None for p in participants)
            ):
                value = sum(p[participant_field] for p in participants)
            return (
                value
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0
                else None
            )

        dragons = raw.get("dragons")
        return team.model_copy(
            update={
                "kills": number("totalKills", "kills"),
                "gold": number("totalGold", "totalGold"),
                "towers": number("towers"),
                "dragons": len(dragons)
                if isinstance(dragons, list)
                else number("dragons"),
                "barons": number("barons"),
            }
        )

    async def get_game_frames(self, game_id, after_source_timestamp=None):
        params = {}
        if after_source_timestamp:
            # Feed timestamps align to ten-second windows. Caller requests overlap.
            aligned = after_source_timestamp - timedelta(
                seconds=after_source_timestamp.second % 10,
                microseconds=after_source_timestamp.microsecond,
            )
            params["startingTime"] = aligned.isoformat().replace("+00:00", "Z")
        payload = await self._request(f"window/{game_id}", params, feed=True)
        return self._frames(payload, game_id)

    def _frames(self, payload, game_id):
        summary = self.game_matches[game_id]
        metadata = payload.get("gameMetadata", {})
        result = []
        for raw in payload.get("frames", []):
            if not raw.get("rfc460Timestamp"):
                continue

            def mapped(side, fallback):
                id = str(
                    metadata.get(f"{side}TeamMetadata", {}).get(
                        "esportsTeamId", fallback.id
                    )
                )
                return next(
                    (t for t in (summary.blue, summary.red) if t.id == id), fallback
                )

            blue = self._stats(raw.get("blueTeam", {}), mapped("blue", summary.blue))
            red = self._stats(raw.get("redTeam", {}), mapped("red", summary.red))
            game_time = raw.get("gameTimeSeconds")
            result.append(
                RawFrame(
                    match_id=summary.match_id,
                    game_id=game_id,
                    source_timestamp=raw["rfc460Timestamp"],
                    game_time_seconds=game_time if isinstance(game_time, int) else None,
                    blue=blue,
                    red=red,
                    status="ended"
                    if raw.get("gameState") == "finished"
                    else "live"
                    if summary.status == "ended"
                    else summary.status,
                    league=summary.league,
                    game_number=summary.game_number,
                )
            )
        return result

    async def get_game_details(self, game_id, timestamp):
        return await self._request(
            f"details/{game_id}",
            {"startingTime": timestamp.isoformat().replace("+00:00", "Z")},
            feed=True,
        )

    async def health(self):
        return {
            "availability": self.last_error or "available",
            "latencyMs": self.latency,
            "errors": self.errors,
        }

    async def close(self):
        await self.client.aclose()


class PublicLoLEsportsProvider(LoLEsportsProvider):
    """Read public schedule data and public stats without executing page scripts."""

    def __init__(self, approved: bool, leagues=None, client=None):
        super().__init__("", approved, client)
        self.leagues = leagues or ["worlds"]
        if any(not re.fullmatch(r"[a-z0-9_-]+", league) for league in self.leagues):
            raise ValueError("Unsupported league slug")
        self.schedule_at = None
        self.schedule_failed = False
        self.scan_next = {}

    async def _public_get(self, url, params=None):
        if not self.approved:
            self.last_error = "access_denied"
            raise AccessDenied("Public live collection requires explicit opt-in")
        started = time.monotonic()
        try:
            response = await self.client.get(url, params=params, follow_redirects=True)
            if response.status_code in (401, 403):
                self.last_error = "access_denied"
                raise AccessDenied("Public source rejected access")
            response.raise_for_status()
            self.last_error = None
            return response
        except httpx.HTTPStatusError as error:
            self.errors += 1
            self.last_error = (
                "rate_limited"
                if error.response.status_code == 429
                else "source_unavailable"
            )
            raise
        except (httpx.RequestError, AccessDenied):
            self.errors += 1
            self.last_error = self.last_error or "source_unavailable"
            raise
        finally:
            self.latency = round((time.monotonic() - started) * 1000)

    @staticmethod
    def _page_events(html):
        decoder = json.JSONDecoder()
        events = {}
        for script in re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.DOTALL):
            if "ApolloSSRDataTransport" not in script:
                continue
            for match in re.finditer(r'\{\s*"__typename"\s*:\s*"EventMatch"', script):
                try:
                    event, _ = decoder.raw_decode(script, match.start())
                except ValueError:
                    continue
                if event.get("id"):
                    events.setdefault(str(event["id"]), event)
        if not events:
            raise ValueError("Public schedule contains no supported match data")
        return list(events.values())

    async def list_matches(self):
        # Until a full refresh succeeds, active get_match calls must respect
        # the collector's shared discovery backoff instead of retrying per game.
        self.schedule_failed = True
        response = await self._public_get(
            "https://lolesports.com/en-US/schedule",
            {"leagues": ",".join(self.leagues)},
        )
        try:
            events = self._page_events(response.text)
            matches = {}
            for event in events:
                if event.get("league", {}).get("slug") not in self.leagues:
                    continue
                # Historical results on the page are not new live sessions.
                # Keep a completed match only if this process followed it live.
                if (
                    event.get("state") == "completed"
                    and event["id"] not in self.matches
                ):
                    continue
                teams = event.get("matchTeams", [])
                if len(teams) != 2:
                    continue
                normalized = {
                    **event,
                    "match": {
                        **event.get("match", {}),
                        "teams": [{**team, "id": team["teamId"]} for team in teams],
                    },
                }
                summary = self._summary(normalized)
                if summary:
                    matches[summary.match_id] = summary
            self.matches = matches
            for match in matches.values():
                if match.game_id:
                    self.game_matches[match.game_id] = match
            self.schedule_at = time.monotonic()
            self.schedule_failed = False
            return sorted(
                matches.values(),
                key=lambda m: (
                    m.status != "live",
                    m.scheduled_at.isoformat() if m.scheduled_at else "",
                ),
            )
        except (KeyError, TypeError, ValueError):
            self.last_error = "source_unavailable"
            self.errors += 1
            raise

    async def get_match(self, match_id):
        # Active games need faster refresh than the 60-second discovery interval.
        if self.schedule_at is None or (
            not self.schedule_failed and time.monotonic() - self.schedule_at >= 10
        ):
            await self.list_matches()
        return self.matches[match_id]

    async def _request(self, path, params=None, feed=False):
        if not feed:
            raise ValueError("Public provider uses schedule HTML for discovery")
        response = await self._public_get(
            f"https://feed.lolesports.com/livestats/v1/{path}", params
        )
        try:
            return response.json()
        except ValueError:
            self.last_error = "source_unavailable"
            self.errors += 1
            raise

    async def get_game_frames(self, game_id, after_source_timestamp=None):
        # With no startingTime the feed returns the game's first ten seconds.
        # Each requested window contains only ten seconds, so overlap must be
        # followed by additional windows to advance beyond the previous cursor.
        latest = utcnow() - timedelta(seconds=20)
        start = after_source_timestamp or (latest - timedelta(seconds=10))
        if game_id in self.scan_next:
            start = max(start, self.scan_next[game_id] - timedelta(seconds=20))
        start = start.replace(second=start.second - start.second % 10, microsecond=0)
        latest = latest.replace(
            second=latest.second - latest.second % 10, microsecond=0
        )
        frames = []
        for _ in range(6):
            if start > latest:
                break
            payload = await self._request(
                f"window/{game_id}",
                {"startingTime": start.isoformat().replace("+00:00", "Z")},
                feed=True,
            )
            window = self._frames(payload, game_id)
            frames.extend(window)
            start += timedelta(seconds=10)
            if any(frame.status == "ended" for frame in window):
                break
        # Track scanned empty windows separately from the last observed frame;
        # otherwise a long source gap traps every retry in the same old range.
        self.scan_next[game_id] = start
        return frames
