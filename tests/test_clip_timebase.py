"""Encoded clip chronology follows observed timestamps rather than configured source FPS."""

import cv2
import numpy as np
import pytest

from roadsentinel.pipeline import clip_fps, write_clip


@pytest.mark.parametrize("sample_fps", [3, 10, 25])
def test_sampled_clip_uses_observed_cadence_at_normal_playback(tmp_path, sample_fps):
    stamps = [index / sample_fps for index in range(sample_fps * 2)]
    frames = []
    for index in range(len(stamps)):
        frame = np.full((120, 160, 3), 32 + index % 200, dtype=np.uint8)
        cv2.putText(frame, f"{stamps[index]:.2f}s", (5, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        frames.append(frame)
    path = tmp_path / "timed.mp4"
    write_clip(path, frames, clip_fps(stamps, 30))
    capture = cv2.VideoCapture(str(path))
    try:
        assert capture.isOpened()
        assert capture.get(cv2.CAP_PROP_FPS) == pytest.approx(sample_fps, rel=0.01)
        assert capture.get(cv2.CAP_PROP_FRAME_COUNT) == len(frames)
        assert capture.get(cv2.CAP_PROP_FRAME_COUNT) / capture.get(cv2.CAP_PROP_FPS) == pytest.approx(2, abs=0.02)
    finally:
        capture.release()


def test_dropped_frame_cadence_preserves_total_span_and_handles_missing_pts():
    # CFR clips preserve the observed span; individual irregular gaps remain a disclosed limitation.
    assert clip_fps([0, 0.1, 0.2, 0.7, 1], 30) == pytest.approx(4)
    assert clip_fps([], 10) == 10
    assert clip_fps([1], 10) == 10
    assert clip_fps([1, 1], 10) == 10
