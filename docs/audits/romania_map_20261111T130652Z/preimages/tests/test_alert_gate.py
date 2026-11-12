from roadsentinel.alerts import AlertGate
from roadsentinel.rates import RateTracker


def ev(typ="very_high_speed", x=100, zone="road", priority="high", tid=1):
    return {"type": typ, "priority": priority, "track_id": tid, "bbox": (x - 10, 90, x + 10, 110),
            "details": {"zone": zone}}


def test_tracker_id_switch_duplicate_is_suppressed_and_counted():
    g = AlertGate()
    assert len(g.filter(0, [ev(tid=1)])) == 1
    assert g.filter(2, [ev(tid=2, x=130)]) == []          # same type, zone, 30 px away, 2 s later
    assert g.stats() == {"duplicate": 1}


def test_a_different_place_or_type_or_a_later_time_is_a_new_alert():
    g = AlertGate()
    g.filter(0, [ev()])
    assert len(g.filter(1, [ev(x=900, tid=2)])) == 1       # far away
    assert len(g.filter(1, [ev("hard_braking", tid=3)])) == 1
    assert len(g.filter(20, [ev(tid=4)])) == 1             # after dedupe_s


def test_cooldown_per_type():
    g = AlertGate({"cooldown_s": {"congestion": 120}, "dedupe_s": 0})
    c = lambda: {"type": "congestion", "priority": "info", "bbox": None, "details": {}}
    assert len(g.filter(0, [c()])) == 1
    assert g.filter(60, [c()]) == []
    assert len(g.filter(130, [c()])) == 1
    assert g.stats() == {"cooldown": 1}


def test_rate_limit_drops_non_critical_but_never_critical():
    g = AlertGate({"max_per_minute": 3, "dedupe_s": 0})
    events = [ev(x=400 * i, tid=i) for i in range(6)]
    assert len(g.filter(0, events)) == 3
    assert g.stats() == {"rate_limit": 3}
    crit = [ev("wrong_way", x=400 * i, tid=50 + i, priority="critical") for i in range(4)]
    assert len(g.filter(1, crit)) == 4
    assert len(g.filter(70, [ev(x=5000, tid=99)])) == 1     # the minute has passed


def test_rate_tracker_measures_fps_from_stream_time():
    r = RateTracker()
    assert r.fps is None
    for i in range(11):
        r.add(i * 2.0)                                       # one frame every 2 s
    assert abs(r.fps - 0.5) < 1e-9
    r.add(0.5)                                               # source restarted
    assert r.fps is None
