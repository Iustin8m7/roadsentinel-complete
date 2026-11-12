"""Regression tests for measured-rate gating of scene-level rules.

Inputs are deterministic test tracks, not traffic footage or incident evidence.
"""

import pytest
from test_rules import CAL, ROAD, TH, det

from roadsentinel.geometry import Zone
from roadsentinel.rules import RuleEngine


def test_congestion_does_not_fire_when_measured_rate_marks_it_unsupported() -> None:
    thresholds = {
        **TH,
        "speed_window_s": 2.0,
        "speed_min_samples": 2,
        "speed_min_span_s": 1.5,
        "min_track_age_s": 0.0,
        "congestion_vehicles": 1,
        "congestion_seconds": 1.0,
    }
    engine = RuleEngine([Zone(ROAD)], thresholds, ["congestion"])
    capabilities = engine.set_rate(0.5)

    assert capabilities["congestion"]["supported"] is False
    events = []
    for timestamp in (0.0, 2.0, 4.0, 6.0):
        events.extend(engine.update(timestamp, [det(1, 40, 400)], CAL))

    assert events == []
    assert engine.tracks[1].speed_kmh() == pytest.approx(0.0, abs=1e-9)


def test_congestion_remains_available_when_rate_supports_configured_sampling() -> None:
    thresholds = {
        **TH,
        "speed_window_s": 2.0,
        "speed_min_samples": 2,
        "speed_min_span_s": 1.5,
        "min_track_age_s": 0.0,
        "congestion_vehicles": 1,
        "congestion_seconds": 1.0,
    }
    engine = RuleEngine([Zone(ROAD)], thresholds, ["congestion"])
    assert engine.set_rate(2.0)["congestion"]["supported"] is True

    events = []
    for timestamp in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5):
        events.extend(engine.update(timestamp, [det(1, 40, 400)], CAL))

    assert [event["type"] for event in events] == ["congestion"]

