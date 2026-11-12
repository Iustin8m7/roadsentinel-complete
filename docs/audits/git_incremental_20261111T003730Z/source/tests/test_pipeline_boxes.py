"""The picture shows the detector's box for a vehicle, not the tracker's smoothed one."""
import numpy as np

from roadsentinel import pipeline
from roadsentinel.rules import RuleEngine


def test_a_trailing_tracker_box_is_replaced_by_the_detector_box_on_the_same_vehicle():
    detected = np.array([[100, 100, 160, 140], [300, 100, 360, 140]], dtype=float)
    assert pipeline.detector_box((110, 108, 185, 160), detected) == (100, 100, 160, 140)


def test_the_tracker_box_is_kept_when_no_detection_overlaps_it_enough():
    detected = np.array([[300, 100, 360, 140]], dtype=float)
    assert pipeline.detector_box((110, 108, 185, 160), detected) == (110, 108, 185, 160)
    assert pipeline.detector_box((110, 108, 185, 160), np.empty((0, 4))) == (110, 108, 185, 160)


def test_draw_outlines_the_shown_box_and_not_the_tracker_box():
    frame = np.zeros((400, 640, 3), dtype=np.uint8)
    objs = [(7, "car", (150, 260), (100, 180, 200, 260))]
    pipeline.draw(frame, [], objs, RuleEngine([], {}), {}, {7: (300, 180, 400, 260)})
    assert frame[180:261, 300].any() and frame[180:261, 400].any()
    assert not frame[200:240, 95:105].any() and not frame[200:240, 195:205].any()


def test_a_flagged_vehicle_gets_a_heavier_outline_than_the_others():
    frame = np.zeros((400, 640, 3), dtype=np.uint8)
    objs = [(1, "car", (150, 260), (100, 180, 200, 260)), (2, "car", (450, 260), (400, 180, 500, 260))]
    pipeline.draw(frame, [], objs, RuleEngine([], {}), {2: (0, 140, 255)})
    plain = int(frame[220, 90:112].any(axis=1).sum())
    flagged = int(frame[220, 390:412].any(axis=1).sum())
    assert flagged > plain > 0
