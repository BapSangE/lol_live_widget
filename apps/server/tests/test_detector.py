from datetime import datetime, timezone, timedelta
from app.events.detector import Detector
from app.models.contracts import RawFrame, TeamState

BASE = datetime(2026, 10, 14, tzinfo=timezone.utc)
def frame(t=0, blue_kills=0, red_kills=0, blue_gold=1000, red_gold=2000, **kw):
    return RawFrame(match_id="m", game_id=kw.pop("game_id", "g"), source_timestamp=BASE+timedelta(seconds=t), game_time_seconds=t,
        blue=TeamState(id="t1",name="T1",short_name="T1",series_wins=2,kills=blue_kills,gold=blue_gold,towers=kw.pop("towers",0),dragons=0,barons=kw.pop("barons",0)),
        red=TeamState(id="gen",name="GEN",short_name="GEN",series_wins=1,kills=red_kills,gold=red_gold,towers=0,dragons=0,barons=0), **kw)

def test_first_frame_and_duplicates_never_retroactively_emit():
    d=Detector()
    assert d.process(frame(0,blue_kills=10),1)==[]
    assert d.process(frame(0,blue_kills=10),2)==[]
    events=d.process(frame(10,blue_kills=11),3)
    assert [e.type for e in events]==["KILL_DELTA"]
    assert d.process(frame(10,blue_kills=11),4)==[]

def test_kill_window_records_facts_not_a_teamfight():
    d=Detector();d.process(frame(),1)
    events=d.process(frame(10,blue_kills=3,red_kills=1),2)
    multi=next(e for e in events if e.type=="MULTIKILL_WINDOW")
    assert "3킬" in multi.message_ko and "1킬" in multi.message_ko
    assert "한타" not in multi.message_ko

def test_null_reset_and_old_frames_do_not_create_events():
    d=Detector();d.process(frame(0,blue_kills=None),1)
    assert d.process(frame(10,blue_kills=5),2)==[]
    assert d.process(frame(5,blue_kills=4),3)==[]
    assert d.process(frame(20,blue_kills=1),4)==[]

def test_gold_change_requires_two_frames_and_500_gold():
    d=Detector();d.process(frame(),1)
    assert not any(e.type=="GOLD_LEAD_CHANGE" for e in d.process(frame(10,blue_gold=2600),2))
    assert any(e.type=="GOLD_LEAD_CHANGE" for e in d.process(frame(20,blue_gold=2700),3))
    assert not any(e.type=="GOLD_LEAD_CHANGE" for e in d.process(frame(30,blue_gold=2800),4))

def test_game_change_and_confirmed_end():
    d=Detector();d.process(frame(),1)
    assert d.process(frame(10,blue_kills=10,game_id="g2"),1)==[]
    events=d.process(frame(20,blue_kills=10,game_id="g2",status="ended",winner_team_id="t1"),2)
    assert [e.type for e in events]==["GAME_END"]
    assert events[0].confidence=="confirmed"

def test_deterministic_ids_and_counter_correction():
    a,b=Detector(),Detector()
    for d in (a,b):d.process(frame(),1)
    ea=a.process(frame(10,barons=1),2);eb=b.process(frame(10,barons=1),2)
    assert ea[0].id==eb[0].id
    assert a.process(frame(10,barons=0),3)==[]
    assert a.process(frame(20,barons=1),4)==[]
