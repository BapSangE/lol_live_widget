from __future__ import annotations

from collections import deque
from datetime import timedelta
from hashlib import sha256

from app.models.contracts import MatchEvent, RawFrame, utcnow


class Detector:
    """Per-game facts only. Corrections never erase or re-announce stored events."""

    def __init__(self):
        self.previous: dict[str, RawFrame] = {}
        self.highwater: dict[tuple[str, str, str], int] = {}
        self.leader: dict[str, int] = {}
        self.candidate: dict[str, tuple[int, int]] = {}
        self.confirmed: set[tuple[str, str, str | None]] = set()
        self.kill_windows: dict[str, deque] = {}

    def process(self, frame: RawFrame, revision: int) -> list[MatchEvent]:
        game = frame.game_id
        previous = self.previous.get(game)
        if previous and frame.source_timestamp < previous.source_timestamp:
            return []
        if previous and frame.source_timestamp == previous.source_timestamp:
            self.previous[game] = frame
            self._seed(frame)
            self.candidate.pop(game, None)
            self.kill_windows.pop(game, None)
            return []
        self.previous[game] = frame
        if previous is None:
            self._seed(frame)
            self.leader[game] = self._sign(self._gold(frame))
            return []
        events: list[MatchEvent] = []
        kills = [0, 0]
        seconds = (frame.source_timestamp - previous.source_timestamp).total_seconds()
        for index, team in enumerate((frame.blue, frame.red)):
            for field, kind, label, cap in (
                ("kills", "KILL_DELTA", "킬 기록", 10),
                ("towers", "TOWER", "타워 파괴", 3),
                ("dragons", "DRAGON", "드래곤 획득", 1),
                ("barons", "BARON", "바론 획득", 1),
            ):
                value = getattr(team, field)
                key = (game, team.id, field)
                old = self.highwater.get(key)
                if value is None:
                    # A missing observation breaks continuity; next value establishes baseline.
                    self.highwater.pop(key, None)
                    continue
                self.highwater[key] = max(value, old if old is not None else value)
                delta = value - old if old is not None else 0
                if 0 < delta <= cap:
                    suffix = f" {delta}회" if delta > 1 else ""
                    events.append(
                        self._event(
                            frame,
                            revision,
                            kind,
                            team.id,
                            f"{team.short_name} {label}{suffix}",
                            len(events),
                        )
                    )
                    if field == "kills":
                        kills[index] = delta
        window = self.kill_windows.setdefault(game, deque())
        cutoff = frame.source_timestamp - timedelta(seconds=20)
        while window and window[0][0] <= cutoff:
            window.popleft()
        if seconds > 20:
            window.clear()
        elif sum(kills):
            window.append((frame.source_timestamp, kills))
            totals = [sum(entry[1][i] for entry in window) for i in range(2)]
            if sum(totals) >= 2:
                events.append(
                    self._event(
                        frame,
                        revision,
                        "MULTIKILL_WINDOW",
                        None,
                        f"관측 구간 {frame.blue.short_name} {totals[0]}킬·{frame.red.short_name} {totals[1]}킬 기록",
                        len(events),
                    )
                )
                window.clear()
        difference = self._gold(frame)
        sign = self._sign(difference)
        leader = self.leader.get(game, 0)
        if (
            difference is not None
            and sign
            and abs(difference) >= 500
            and leader
            and sign != leader
        ):
            candidate, count = self.candidate.get(game, (sign, 0))
            count = count + 1 if candidate == sign else 1
            self.candidate[game] = (sign, count)
            if count >= 2:
                team = frame.blue if sign > 0 else frame.red
                events.append(
                    self._event(
                        frame,
                        revision,
                        "GOLD_LEAD_CHANGE",
                        team.id,
                        f"{team.short_name} 골드 우위 역전 · {abs(difference):,}골드",
                        len(events),
                    )
                )
                self.leader[game] = sign
                self.candidate.pop(game, None)
        else:
            self.candidate.pop(game, None)
            if not leader and sign:
                self.leader[game] = sign
        for kind, team_id, label in (
            ("ELDER", frame.elder_team_id, "장로 드래곤 획득"),
            ("DRAGON_SOUL", frame.soul_team_id, "드래곤 영혼 획득"),
            (
                "GAME_END",
                frame.winner_team_id if frame.status == "ended" else None,
                "게임 승리",
            ),
        ):
            key = (game, kind, team_id)
            team = next((t for t in (frame.blue, frame.red) if t.id == team_id), None)
            if team and key not in self.confirmed:
                self.confirmed.add(key)
                events.append(
                    self._event(
                        frame,
                        revision,
                        kind,
                        team.id,
                        f"{team.short_name} {label}",
                        len(events),
                        "confirmed",
                    )
                )
        return events

    def _seed(self, frame: RawFrame):
        for team in (frame.blue, frame.red):
            for field in ("kills", "towers", "dragons", "barons"):
                value = getattr(team, field)
                key = (frame.game_id, team.id, field)
                if value is not None:
                    self.highwater[key] = max(value, self.highwater.get(key, value))
                else:
                    self.highwater.pop(key, None)
        # Already-present official objectives aren't newly observed acquisitions.
        for kind, team in (
            ("ELDER", frame.elder_team_id),
            ("DRAGON_SOUL", frame.soul_team_id),
        ):
            if team:
                self.confirmed.add((frame.game_id, kind, team))

    @staticmethod
    def _gold(frame):
        if frame.blue.gold is None or frame.red.gold is None:
            return None
        return frame.blue.gold - frame.red.gold

    @staticmethod
    def _sign(value):
        return 0 if value is None or value == 0 else (1 if value > 0 else -1)

    @staticmethod
    def _event(frame, revision, kind, team, message, index, confidence="derived"):
        timestamp = frame.source_timestamp.isoformat()
        event_id = sha256(
            f"{frame.game_id}|{kind}|{team or ''}|{timestamp}|{index}".encode()
        ).hexdigest()
        return MatchEvent(
            id=event_id,
            match_id=frame.match_id,
            game_id=frame.game_id,
            type=kind,
            game_time_seconds=frame.game_time_seconds,
            occurred_at=frame.source_timestamp if confidence == "confirmed" else None,
            observed_at=utcnow(),
            team_id=team,
            priority="critical"
            if kind == "GAME_END"
            else ("normal" if kind == "KILL_DELTA" else "important"),
            message_ko=message,
            confidence=confidence,
            source_revision=revision,
        )
