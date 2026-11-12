"""ONNX/Supervision renders fresh detector coordinates, never Kalman-only predictions."""

import numpy as np
import pytest

from roadsentinel.detector import Detections, create_tracker, to_supervision


def test_tracker_ids_attach_to_current_detector_pixels_not_predicted_boxes():
    tracker = create_tracker(10)
    observed = []
    for shift in (0, 8, 24, 41):
        box = np.array([[20 + shift, 30, 100 + shift, 130]], dtype=np.float32)
        detected = Detections(box, np.array([0.91]), np.array([2]), 0.0)
        result = tracker.update_with_detections(to_supervision(detected))
        if len(result):
            np.testing.assert_array_equal(result.xyxy, box)
            assert result.class_id.tolist() == [2]
            assert result.confidence[0] == pytest.approx(0.91)
            observed.extend(result.tracker_id.tolist())
    assert observed and len(set(observed)) == 1
    empty = Detections(np.empty((0, 4), dtype=np.float32), np.empty(0), np.empty(0, dtype=int), 0.0)
    assert len(tracker.update_with_detections(to_supervision(empty))) == 0


def test_crossing_or_unmatched_tracks_never_invent_rendered_geometry():
    tracker = create_tracker(10)
    for boxes in ([[10, 10, 40, 50], [80, 10, 110, 50]], [[25, 10, 55, 50], [65, 10, 95, 50]], [[40, 10, 70, 50]]):
        raw = np.asarray(boxes, dtype=np.float32)
        detected = Detections(raw, np.full(len(raw), 0.9), np.full(len(raw), 2), 0.0)
        result = tracker.update_with_detections(to_supervision(detected))
        assert all(any(np.array_equal(box, fresh) for fresh in raw) for box in result.xyxy)


def test_nullable_editor_cutoff_normalizes_without_changing_approved_revision():
    from roadsentinel.pipeline import load_camera

    approved = {"calibration": None, "min_y": None, "zones": []}
    runtime, _, _ = load_camera(None, approved)
    assert runtime["min_y"] == 0
    assert approved["min_y"] is None


def test_flagged_observation_has_stronger_outline_at_actual_detector_box():
    from roadsentinel.pipeline import draw
    from roadsentinel.rules import RuleEngine

    frame = np.zeros((400, 640, 3), dtype=np.uint8)
    objects = [(1, "car", (150, 260), (100, 180, 200, 260)), (2, "car", (450, 260), (400, 180, 500, 260))]
    draw(frame, [], objects, RuleEngine([], {}), {2: (0, 140, 255)}, {1: 0.9, 2: 0.8})
    plain = frame[220, 90:112].any(axis=1).sum()
    flagged = frame[220, 390:412].any(axis=1).sum()
    assert flagged > plain > 0
