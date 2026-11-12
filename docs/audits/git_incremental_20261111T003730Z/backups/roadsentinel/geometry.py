"""Pixel <-> road-plane calibration and zone helpers."""
import cv2
import numpy as np


class Calibration:
    """Maps image points to metres on the road plane via a homography."""

    def __init__(self, source, width_m, length_m):
        src = np.array(source, dtype=np.float32)
        dst = np.array([[0, 0], [width_m, 0], [width_m, length_m], [0, length_m]], dtype=np.float32)
        self.m = cv2.getPerspectiveTransform(src, dst)

    @classmethod
    def from_points(cls, pairs):
        """Homography from >= 4 (pixel, metre) pairs on the road plane: [[px, py, X_m, Y_m], ...].
        With more than 4 pairs the fit is robust (RANSAC) and least-squares refined. Lens distortion
        is NOT corrected: wide-angle/fisheye cameras need an undistortion step first (docs/CALIBRATION.md)."""
        arr = np.array(pairs, dtype=np.float64)
        if arr.ndim != 2 or arr.shape[1] != 4 or len(arr) < 4:
            raise ValueError("need at least 4 [px, py, x_m, y_m] reference points")
        self = cls.__new__(cls)
        method = 0 if len(arr) == 4 else cv2.RANSAC
        self.m, _ = cv2.findHomography(arr[:, :2], arr[:, 2:], method, 0.5)
        if self.m is None:
            raise ValueError("the reference points do not define a homography (collinear?)")
        return self

    def to_metres(self, points):
        pts = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
        return cv2.perspectiveTransform(pts, self.m).reshape(-1, 2)


class Zone:
    def __init__(self, cfg):
        self.id = cfg["id"]
        self.name = cfg["name"]
        self.kind = cfg["kind"]
        self.polygon = np.array(cfg["polygon"], dtype=np.int32)
        d = cfg.get("direction")
        self.direction = np.array(d, dtype=np.float32) / np.linalg.norm(d) if d else None

    def contains(self, point):
        return cv2.pointPolygonTest(self.polygon, (float(point[0]), float(point[1])), False) >= 0
