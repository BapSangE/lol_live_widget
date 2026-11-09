from datetime import UTC, datetime, timedelta

from app.events.detector import Detector
from app.models.contracts import RawFrame, TeamState

BASE = datetime(2026, 10, 14, tzinfo=UTC)


def frame(t=0, blue_kills=0, red_kills=0, blue_gold=1000, red_gold=2000, **kw):
    return RawFrame(
        match_id="m",
        game_id=kw.pop("game_id", "g"),
        source_timestamp=BASE + timedelta(seconds=t),
        game_time_seconds=t,
        blue=TeamState(
            id="t1",
            name="T1",
            short_name="T1",
            series_wins=2,
            kills=blue_kills,
            gold=blue_gold,
            towers=kw.pop("towers", 0),
            dragons=0,
            barons=kw.pop("barons", 0),
        ),
        red=TeamState(
            id="gen",
            name="GEN",
            short_name="GEN",
            series_wins=1,
            kills=red_kills,
            gold=red_gold,
            towers=0,
            dragons=0,
            barons=0,
        ),
        **kw,
    )


def test_first_frame_and_duplicates_never_retroactively_emit():
    d = Detector()
    assert d.process(frame(0, blue_kills=10), 1) == []
    assert d.process(frame(0, blue_kills=10), 2) == []
    events = d.process(frame(10, blue_kills=11), 3)
    assert [e.type for e in events] == ["KILL_DELTA"]
    assert d.process(frame(10, blue_kills=11), 4) == []


def test_kill_window_records_facts_not_a_teamfight():
    d = Detector()
    d.process(frame(), 1)
    events = d.process(frame(10, blue_kills=3, red_kills=1), 2)
    multi = next(e for e in events if e.type == "MULTIKILL_WINDOW")
    assert "3킬" in multi.message_ko and "1킬" in multi.message_ko
    assert "한타" not in multi.message_ko


def test_null_reset_and_old_frames_do_not_create_events():
    d = Detector()
    d.process(frame(0, blue_kills=None), 1)
    assert d.process(frame(10, blue_kills=5), 2) == []
    assert d.process(frame(5, blue_kills=4), 3) == []
    assert d.process(frame(20, blue_kills=1), 4) == []


def test_gold_change_requires_two_frames_and_500_gold():
    d = Detector()
    d.process(frame(), 1)
    assert not any(
        e.type == "GOLD_LEAD_CHANGE" for e in d.process(frame(10, blue_gold=2600), 2)
    )
    assert any(
        e.type == "GOLD_LEAD_CHANGE" for e in d.process(frame(20, blue_gold=2700), 3)
    )
    assert not any(
        e.type == "GOLD_LEAD_CHANGE" for e in d.process(frame(30, blue_gold=2800), 4)
    )


def test_game_change_and_confirmed_end():
    d = Detector()
    d.process(frame(), 1)
    assert d.process(frame(10, blue_kills=10, game_id="g2"), 1) == []
    events = d.process(
        frame(20, blue_kills=10, game_id="g2", status="ended", winner_team_id="t1"), 2
    )
    assert [e.type for e in events] == ["GAME_END"]
    assert events[0].confidence == "confirmed"


def test_deterministic_ids_and_counter_correction():
    a, b = Detector(), Detector()
    for d in (a, b):
        d.process(frame(), 1)
    ea = a.process(frame(10, barons=1), 2)
    eb = b.process(frame(10, barons=1), 2)
    assert ea[0].id == eb[0].id
    assert a.process(frame(10, barons=0), 3) == []
    assert a.process(frame(20, barons=1), 4) == []


def test_multikill_window_combines_adjacent_frames_once():
    d = Detector()
    d.process(frame(), 1)
    assert not any(
        e.type == "MULTIKILL_WINDOW" for e in d.process(frame(10, blue_kills=1), 2)
    )
    events = d.process(frame(20, blue_kills=1, red_kills=1), 3)
    multi = next(e for e in events if e.type == "MULTIKILL_WINDOW")
    assert "1킬" in multi.message_ko
    assert not any(
        e.type == "MULTIKILL_WINDOW"
        for e in d.process(frame(30, blue_kills=1, red_kills=1), 4)
    )


def test_same_timestamp_null_correction_breaks_counter_continuity():
    d = Detector()
    d.process(frame(0, blue_kills=1), 1)
    d.process(frame(10, blue_kills=2), 2)
    assert d.process(frame(10, blue_kills=None), 3) == []
    assert d.process(frame(20, blue_kills=3), 4) == []


def player(kills=0, deaths=0, participant_id=3, name="T1 Faker", team_id="t1"):
    return {
        "participant_id": participant_id,
        "name": name,
        "team_id": team_id,
        "kills": kills,
        "deaths": deaths,
    }


def test_player_counters_skip_baseline_duplicates_corrections_and_new_sets():
    d = Detector()
    assert d.process(frame(0, players=[player(5, 2)]), 1) == []
    changed = frame(10, blue_kills=1, players=[player(6, 3)])
    events = d.process(changed, 2)
    assert [(e.type, e.message_ko) for e in events] == [
        ("PLAYER_KILL", "T1 Faker 킬 +1"),
        ("PLAYER_DEATH", "T1 Faker 사망 +1"),
    ]
    assert d.process(changed, 3) == []
    assert d.process(frame(10, blue_kills=1, players=[player(5, 2)]), 4) == []
    assert d.process(frame(20, blue_kills=1, players=[player(6, 3)]), 5) == []
    assert d.process(frame(30, game_id="g2", players=[player(2, 1)]), 1) == []


def test_missing_player_stats_restart_baseline_without_inventing_names_or_kills():
    d = Detector()
    d.process(frame(0, players=[player(2)]), 1)
    d.process(frame(10, players=[]), 2)
    assert d.process(frame(20, players=[player(4)]), 3) == []
    d.process(frame(30, players=[player(None, None)]), 4)
    assert d.process(frame(40, players=[player(6, 3)]), 5) == []
    events = d.process(frame(50, players=[player(7, 4)]), 6)
    assert {e.message_ko for e in events} == {"T1 Faker 킬 +1", "T1 Faker 사망 +1"}


def test_multiple_players_are_reported_independently_with_team_fallback_for_partial_data():
    d = Detector()
    d.process(
        frame(
            0,
            players=[
                player(),
                player(participant_id=8, name="GEN Chovy", team_id="gen"),
            ],
        ),
        1,
    )
    events = d.process(
        frame(
            10,
            blue_kills=2,
            red_kills=1,
            players=[
                player(1, 1),
                player(1, 1, participant_id=8, name="GEN Chovy", team_id="gen"),
            ],
        ),
        2,
    )
    assert len([e for e in events if e.type == "PLAYER_KILL"]) == 2
    assert len([e for e in events if e.type == "PLAYER_DEATH"]) == 2
    assert [(e.team_id, e.message_ko) for e in events if e.type == "KILL_DELTA"] == [
        ("t1", "T1 킬 기록 2회")
    ]
    assert not any("처치" in e.message_ko for e in events)
