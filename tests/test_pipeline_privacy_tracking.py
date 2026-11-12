"""Person boxes remain usable for redaction without creating tracker identities by default."""

import numpy as np

from roadsentinel.detector import Detections
from roadsentinel.pipeline import tracking_detections


def _prediction() -> Detections:
    return Detections(
        xyxy=np.array([[1, 2, 3, 4], [10, 20, 30, 40], [50, 60, 80, 90]], dtype=np.float32),
        confidence=np.array([0.9, 0.8, 0.7], dtype=np.float32),
        class_id=np.array([0, 2, 7], dtype=np.int64),
        latency_ms=12.5,
    )


def test_people_are_not_passed_to_tracker_by_default() -> None:
    original = _prediction()
    tracked = tracking_detections(original)

    assert original.class_id.tolist() == [0, 2, 7]  # original still supports pre-tracker redaction
    assert tracked.class_id.tolist() == [2, 7]
    assert tracked.xyxy.tolist() == [[10.0, 20.0, 30.0, 40.0], [50.0, 60.0, 80.0, 90.0]]
    assert tracked.latency_ms == original.latency_ms


def test_person_tracking_is_kept_only_when_the_specific_rule_requires_it() -> None:
    prediction = _prediction()
    assert tracking_detections(prediction, allow_person=True) is prediction

