"""Rules engine tests on synthetic tracks (no video or model needed).

Calibration used everywhere: 10 px = 1 m, road plane 10 m wide x 100 m long.
"""
import pytest

from roadsentinel.geometry import Calibration, Zone
from roadsentinel.rules import RuleEngine

FPS = 25
CAL = Calibration([[0, 0], [100, 0], [100, 1000], [0, 1000]], 10, 100)
TH = {
    "speed_limit_kmh": 130, "very_high_speed_kmh": 150, "stopped_speed_kmh": 5, "stopped_seconds": 4,
    "hard_brake_mps2": 4.5, "headway_seconds": 0.8, "headway_min_speed_kmh": 60, "lane_change_m": 3.0,
    "lane_change_window_s": 1.5, "wrong_way_min_px": 120, "congestion_vehicles": 3,
    "congestion_avg_speed_kmh": 30, "congestion_seconds": 2,
}
ROAD = {"id": "road", "name": "Carosabil", "kind": "carriageway", "direction": [0, 1],
        "polygon": [[0, 0], [80, 0], [80, 1000], [0, 1000]]}
SHOULDER = {"id": "shoulder", "name": "Bandă de urgență", "kind": "emergency_lane",
            "polygon": [[80, 0], [100, 0], [100, 1000], [80, 1000]]}


def engine(rules=None, th=None):
    return RuleEngine([Zone(ROAD), Zone(SHOULDER)], {**TH, **(th or {})}, rules)


def det(tid, x, y, cls="car"):
    return (tid, cls, (x, y), (x - 10, y - 20, x + 10, y))


def drive(eng, seconds, positions):
    """positions(t) -> list of detections at time t. Returns all events, in order."""
    events = []
    for i in range(int(seconds * FPS)):
        t = i / FPS
        events += eng.update(t, positions(t), CAL)
    return events


def types(events):
    return [e["type"] for e in events]


def kmh_to_px_per_s(kmh):
    return kmh / 3.6 * 10


def test_speed_estimate_matches_ground_truth():
    eng = engine()
    v = kmh_to_px_per_s(90)
    drive(eng, 3, lambda t: [det(1, 40, 50 + v * t)])
    assert eng.tracks[1].speed_kmh() == pytest.approx(90, abs=1)


def test_very_high_speed_fires_once_with_measured_speed():
    eng = engine()
    v = kmh_to_px_per_s(170)
    events = drive(eng, 4, lambda t: [det(1, 40, 10 + v * t)])
    assert types(events) == ["very_high_speed"]
    assert events[0]["speed_kmh"] == pytest.approx(170, abs=2)
    assert events[0]["priority"] == "high"


def test_normal_speed_raises_nothing():
    eng = engine()
    v = kmh_to_px_per_s(110)
    assert drive(eng, 4, lambda t: [det(1, 40, 10 + v * t)]) == []


def test_stopped_in_emergency_lane_after_dwell_time():
    eng = engine()
    events = drive(eng, 6, lambda t: [det(1, 90, 500)])
    assert types(events) == ["stopped_emergency_lane"]
    assert events[0]["details"]["dwell_s"] >= TH["stopped_seconds"]


def test_short_stop_does_not_fire():
    eng = engine()
    assert drive(eng, 3, lambda t: [det(1, 90, 500)]) == []


def test_wrong_way_on_steady_reverse_motion():
    eng = engine()
    v = kmh_to_px_per_s(60)
    events = drive(eng, 4, lambda t: [det(1, 40, 900 - v * t)])
    assert "wrong_way" in types(events)
    assert next(e for e in events if e["type"] == "wrong_way")["priority"] == "critical"


def test_tracker_id_jump_is_not_wrong_way():
    # Same ID teleports 300 px backwards once (tracker swapped cars), otherwise moves correctly.
    eng = engine()
    v = kmh_to_px_per_s(60)
    events = drive(eng, 4, lambda t: [det(1, 40, 600 + v * t - (300 if t > 2 else 0))])
    assert "wrong_way" not in types(events)


def test_pedestrian_on_road_is_critical():
    eng = engine()
    events = drive(eng, 1, lambda t: [det(7, 40, 500, cls="person")])
    assert types(events) == ["pedestrian_on_road"]


def test_tailgating_needs_sustained_short_headway():
    eng = engine()
    v = kmh_to_px_per_s(100)                 # 27.8 m/s
    gap_px = 100                              # 10 m -> 0.36 s headway
    events = drive(eng, 4, lambda t: [det(1, 40, 10 + v * t), det(2, 40, 10 + gap_px + v * t)])
    assert "tailgating" in types(events)


def test_hard_braking():
    eng = engine()
    v0 = kmh_to_px_per_s(100)
    a = 7 * 10                                # 7 m/s^2 in px/s^2
    def pos(t):
        tb = max(0.0, t - 1.5)                # cruise 1.5 s, then brake
        return [det(1, 40, 10 + v0 * t - 0.5 * a * tb ** 2)]
    assert "hard_braking" in types(drive(eng, 3.5, pos))


def test_congestion_is_per_zone_and_fires_once():
    eng = engine()
    v = kmh_to_px_per_s(10)
    jam = lambda t: [det(i, 20 + 15 * (i % 4), 100 + 80 * i + v * t) for i in range(4)]
    events = drive(eng, 6, jam)
    assert types(events) == ["congestion"]
    assert events[0]["details"]["zone"] == "road"


def test_disabled_rules_never_fire():
    eng = engine(rules=["congestion"])
    v = kmh_to_px_per_s(170)
    assert drive(eng, 4, lambda t: [det(1, 40, 10 + v * t)]) == []


def hard_stop(cls):
    """60 km/h for 2 s, then a stop within 1.5 s, then standing still."""
    v = kmh_to_px_per_s(60)

    def positions(t):
        if t < 2:
            y = v * t
        elif t < 3.5:
            dt = t - 2
            y = v * 2 + v * dt - v / 1.5 * dt * dt / 2
        else:
            y = v * 2 + v * 1.5 / 2
        return [det(1, 40, 100 + y, cls)]
    return positions


def test_hard_stop_on_the_road_is_a_probable_crash():
    assert "probable_crash" in types(drive(engine(["probable_crash"]), 6, hard_stop("car")))


def test_crash_ignore_classes_skips_trams_braking_at_a_stop():
    eng = engine(["probable_crash"], {"crash_ignore_classes": ["bus"]})
    assert "probable_crash" not in types(drive(eng, 6, hard_stop("bus")))
    eng = engine(["probable_crash"], {"crash_ignore_classes": ["bus"]})
    assert "probable_crash" in types(drive(eng, 6, hard_stop("car")))
