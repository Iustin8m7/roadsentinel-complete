"""Sampling-rate behaviour, capabilities, and the near-miss / object / crash definitions.

All synthetic: these tests prove the code does what docs/RULES.md says, NOT that it is accurate on
real footage (that needs training/eval.py on a labelled held-out set)."""
import pytest
from test_rules import CAL, ROAD, SHOULDER, TH, det, interacting_stop, kmh_to_px_per_s, types

from roadsentinel.geometry import Zone
from roadsentinel.rules import RuleEngine, rule_capabilities

LOW = {"speed_window_s": 12, "speed_min_samples": 3, "speed_min_span_s": 4, "sustain_s": 12,
       "sustain_samples": 2, "min_track_age_s": 4}


def test_empty_rules_means_detection_only_without_geometry():
    engine = RuleEngine([], {}, rules=[])
    engine.set_rate(1.0)
    assert engine.update(0.0, [(1, "car", (10, 20), (0, 0, 20, 20))], None) == []
    assert len(engine.tracks[1].speeds) == 0


def run_at(fps, seconds, positions, th=None, rules=None):
    eng = RuleEngine([Zone(ROAD), Zone(SHOULDER)], {**TH, **(th or {})}, rules)
    eng.set_rate(fps)
    events, n = [], int(seconds * fps)
    for i in range(n):
        t = i / fps
        events += eng.update(t, positions(t), CAL)
    return eng, events


def speeder(kmh):
    v = kmh_to_px_per_s(kmh)
    return lambda t: [det(1, 40, 10 + v * t)]


@pytest.mark.parametrize("fps", [25, 10, 5])
def test_default_config_alerts_at_normal_rates(fps):
    _, events = run_at(fps, 4, speeder(170), rules=["very_high_speed"])
    assert types(events) == ["very_high_speed"]
    assert "confidence" not in events[0]["details"]


@pytest.mark.parametrize("fps", [2, 1, 0.5])
def test_default_config_cannot_work_at_low_rates_and_says_so(fps):
    eng, events = run_at(fps, 60, speeder(100), th={"very_high_speed_kmh": 80}, rules=["very_high_speed"])
    assert events == []
    assert "very_high_speed" in eng.unsupported
    assert "cadre/s" in eng.unsupported["very_high_speed"]


@pytest.mark.parametrize("fps", [2, 1, 0.5])
def test_low_rate_mode_alerts_and_marks_lower_confidence(fps):
    # 100 km/h = 27.8 m/s. Keep the car inside the 100 m road: restart the position per pass.
    v = kmh_to_px_per_s(100)
    eng, events = run_at(fps, 14, lambda t: [det(1, 40, 10 + v * t * 0.5)], th={**LOW, "very_high_speed_kmh": 40},
                         rules=["very_high_speed"])
    assert "very_high_speed" not in eng.unsupported
    assert types(events) == ["very_high_speed"]
    d = events[0]["details"]
    assert d["confidence"] == "low" and d["rate_mode"] == "low_fps"


def test_low_rate_speed_is_still_accurate_on_a_clean_track():
    v = kmh_to_px_per_s(60)
    eng, _ = run_at(0.5, 14, lambda t: [det(1, 40, 10 + v * t)], th=LOW, rules=["very_high_speed"])
    assert eng.tracks[1].speed_kmh() == pytest.approx(60, abs=2)


def test_capabilities_are_computed_from_the_measured_rate():
    caps = rule_capabilities(TH, 0.5)
    assert caps["pedestrian_on_road"]["supported"] and caps["object_on_roadway"]["supported"]
    assert not caps["very_high_speed"]["supported"] and not caps["hard_braking"]["supported"]
    assert caps["very_high_speed"]["min_fps"] == 5.0
    assert not rule_capabilities(TH, 8)["wrong_way"]["supported"]      # needs 10 fps
    assert rule_capabilities(TH, 25)["wrong_way"]["supported"]
    assert rule_capabilities({**TH, **LOW}, 0.5)["very_high_speed"]["supported"]
    assert not rule_capabilities({**TH, **LOW}, 0.5)["hard_braking"]["supported"]  # never at 0.5 fps


def test_pedestrian_rule_needs_no_speed_so_it_works_at_any_rate():
    eng, events = run_at(0.5, 8, lambda t: [det(9, 40, 400, "person")], rules=["pedestrian_on_road"])
    assert types(events) == ["pedestrian_on_road"] and eng.unsupported == {}


# ---------------------------------------------------------------- near miss
def converging(gap_m, closing_kmh):
    """Two cars on the same lane, the follower closing on the leader."""
    v = kmh_to_px_per_s(closing_kmh)
    lead_y = 300 + gap_m * 10

    def positions(t):
        return [det(1, 40, 100 + v * t), det(2, 41, lead_y + kmh_to_px_per_s(20) * t)]
    return positions


def test_near_miss_fires_when_ttc_is_below_the_threshold():
    _, events = run_at(25, 3, converging(8, 80), rules=["near_miss"])
    assert types(events) == ["near_miss"]
    d = events[0]["details"]
    assert d["ttc_s"] < 1.5 and d["distance_m"] < 15 and {1, 2} == {events[0]["track_id"], d["other_track"]}


def test_no_near_miss_when_far_or_slowly_closing():
    assert run_at(25, 3, converging(60, 80), rules=["near_miss"])[1] == []        # far apart
    assert run_at(25, 3, converging(8, 22), rules=["near_miss"])[1] == []         # closing at 2 km/h
    assert types(run_at(25, 3, converging(8, 80), th={"near_miss_ttc_s": 0.0}, rules=["near_miss"])[1]) == []


def test_near_miss_fires_once_per_pair():
    _, events = run_at(25, 5, converging(8, 80), rules=["near_miss"])
    assert types(events).count("near_miss") == 1


# ---------------------------------------------------------------- object on roadway
def test_static_object_in_road_zone_fires_after_the_dwell_time():
    _, events = run_at(5, 8, lambda t: [det(5, 40, 400, "object")], rules=["object_on_roadway"])
    assert types(events) == ["object_on_roadway"]
    assert events[0]["details"]["dwell_s"] >= 4.5


def test_moving_object_or_short_dwell_is_not_debris():
    assert run_at(5, 3, lambda t: [det(5, 40, 400, "object")], rules=["object_on_roadway"])[1] == []
    assert run_at(5, 8, lambda t: [det(5, 40, 400 + 40 * t, "object")], rules=["object_on_roadway"])[1] == []


def test_object_outside_a_road_zone_is_ignored():
    assert run_at(5, 8, lambda t: [det(5, 95, 400, "object")], rules=["object_on_roadway"])[1] != []  # shoulder counts
    off_road = [[0, 0], [10, 0], [10, 10], [0, 10]]
    eng = RuleEngine([Zone({**ROAD, "polygon": off_road})], TH, ["object_on_roadway"])
    events = []
    for i in range(50):
        events += eng.update(i / 5, [det(5, 40, 400, "object")], CAL)
    assert events == []


# ---------------------------------------------------------------- probable crash
def hard_stop_then(resume):
    v = kmh_to_px_per_s(60)

    def positions(t):
        if t < 2:
            y = v * t
        elif t < 3.5:
            dt = t - 2
            y = v * 2 + v * dt - v / 1.5 * dt * dt / 2
        elif resume and t > 4.5:
            y = v * 2 + v * 1.5 / 2 + v * (t - 4.5)
        else:
            y = v * 2 + v * 1.5 / 2
        lead_y = 590 - v * max(0, 2.5 - t)
        return [det(1, 40, 100 + y), det(2, 40, lead_y)]
    return positions


def test_crash_needs_the_vehicle_to_stay_stationary_after_the_stop():
    assert "probable_crash" in types(run_at(25, 7, interacting_stop(), rules=["probable_crash"])[1])
    # braking hard and driving on again is not a crash
    assert "probable_crash" not in types(run_at(25, 7, hard_stop_then(True), rules=["probable_crash"])[1])


def test_crash_stationary_time_is_configurable():
    # at 3.5 s the car stops; a 10 s hold has not elapsed by 7 s
    _, events = run_at(25, 7, hard_stop_then(False), th={"crash_stationary_s": 10}, rules=["probable_crash"])
    assert events == []
