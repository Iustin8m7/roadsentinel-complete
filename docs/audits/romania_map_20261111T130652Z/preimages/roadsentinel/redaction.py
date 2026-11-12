"""Privacy redaction of video frames (heuristic; no torch/ultralytics dependency).

Heads are the top third of a person box; the plate band is the bottom 35% of a vehicle box;
the windshield is the top half of cars/trucks/buses larger than 10% of the frame height. It
cannot cover missed detections, small/night targets or unusual plate positions: it is a
heuristic, not a guarantee. Redaction runs before any frame is written, stored or sent.
"""
import os

import cv2
import numpy as np


def redaction_mode():
    """Redaction is ON by default. "off" needs the explicit RS_ALLOW_UNREDACTED=1 as well, and
    is then reported to the backend as "off" (shown as FĂRĂ REDACTARE), never relabelled."""
    mode = os.environ.get("RS_REDACTION", "full")
    if mode not in {"full", "heads_only", "off"}:
        raise ValueError("RS_REDACTION must be full, heads_only or off")
    if mode == "off" and os.environ.get("RS_ALLOW_UNREDACTED") != "1":
        raise ValueError(
            "RS_REDACTION=off stores unblurred faces and plates; set RS_ALLOW_UNREDACTED=1 to confirm"
        )
    return mode


def blur_region(frame, box):
    """Blur a clipped region; reject inverted or wholly off-frame boxes."""
    x1, y1, x2, y2 = box
    h, w = frame.shape[:2]
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w, int(np.ceil(x2))), min(h, int(np.ceil(y2)))
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2]
    kernel = max(3, int(max(roi.shape[:2]) * 0.3) | 1)
    frame[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (kernel, kernel), 0)


def blur_people(frame, boxes):
    """Blur every detected person's head, including vehicle occupants."""
    for x1, y1, x2, y2 in boxes:
        if x2 > x1 and y2 > y1:
            blur_region(frame, (x1, y1, x2, min(y2, y1 + max(4, (y2 - y1) / 3))))


def blur_vehicle_plate(frame, box):
    """Conservative bumper band, replaceable with a plate detector later."""
    x1, y1, x2, y2 = box
    if x2 > x1 and y2 > y1:
        blur_region(frame, (x1, y1 + 0.65 * (y2 - y1), x2, y2))


def redact_frame(frame, detections, mode=None):
    """Redact all detections before tracking filters or any evidence output.

    A vehicle at least 10% of the frame height is considered close enough
    for windshield redaction. Plate bands apply at every distance.
    This heuristic cannot cover missed detections or unusual plate positions.
    """
    mode = redaction_mode() if mode is None else mode
    if mode not in {"full", "heads_only", "off"}:
        raise ValueError("RS_REDACTION must be full, heads_only or off")
    if mode == "off":  # demo: no blurring at all
        return
    blur_people(frame, [box for cls, box in detections if cls == "person"])
    if mode == "full":
        for cls, box in detections:
            if cls in {"car", "truck", "bus", "motorcycle"}:
                blur_vehicle_plate(frame, box)
            x1, y1, x2, y2 = box
            if cls in {"car", "truck", "bus"} and y2 - y1 >= 0.1 * frame.shape[0]:
                blur_region(frame, (x1, y1, x2, y1 + 0.5 * (y2 - y1)))
    return frame
