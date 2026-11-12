from __future__ import annotations

import math

import numpy as np
import pytest
from app.services.offline_heatmap import heatmap, observation_from_roi, timeline, validate_frame_record


def _frame(sequence: int, pts: float, observations: list[dict] | None = None) -> dict:
    return {
        "record_type": "sample",
        "schema_version": 1,
        "source_frame_index": sequence * 30,
        "sample_sequence": sequence,
        "pts_seconds": pts,
        "observations": observations or [],
    }


def _obs(x: float, y: float, name: str = "car", track_id: int | None = 1) -> dict:
    return {
        "class_id": {"bicycle": 1, "car": 2, "motorcycle": 3, "bus": 5, "truck": 7}[name],
        "class_name": name,
        "confidence": 0.9,
        "bbox_normalized": [x - 0.01, y - 0.02, x + 0.01, y],
        "anchor_normalized": [x, y],
        "track_id": track_id,
    }


def _aggregate(frames, **kwargs):
    start_s = kwargs.pop("start_s", 0)
    end_s = kwargs.pop("end_s", 20)
    return heatmap(
        frames,
        width=1050,
        height=589,
        crop={"x": 0, "y": 0, "width": 1, "height": 1},
        duration_s=20,
        sample_fps=1,
        start_s=start_s,
        end_s=end_s,
        **kwargs,
    )


def test_crop_detection_maps_to_normalized_full_source_coordinates() -> None:
    result = observation_from_roi(
        box=(280, 180, 320, 200),
        class_id=2,
        class_name="car",
        confidence=0.8,
        track_id=42,
        crop_px=(100, 50, 800, 500),
        source_width=1050,
        source_height=589,
    )
    assert result is not None
    assert result["anchor_normalized"] == pytest.approx((400 / 1050, 250 / 589))
    assert result["bbox_normalized"] == pytest.approx((380 / 1050, 230 / 589, 420 / 1050, 250 / 589))
    assert (
        observation_from_roi(
            box=(1, 1, 10, 10),
            class_id=0,
            class_name="person",
            confidence=0.9,
            track_id=None,
            crop_px=(0, 0, 1050, 589),
            source_width=1050,
            source_height=589,
        )
        is None
    )


def test_density_is_localized_sums_weight_and_zero_samples_are_not_missing() -> None:
    single = _aggregate([_frame(1, 1, [_obs(0.4, 0.45)])], grid_width=128)
    matrix = np.asarray(single["values"]).reshape(single["grid_height"], single["grid_width"])
    peak_y, peak_x = np.unravel_index(matrix.argmax(), matrix.shape)
    assert peak_x / single["grid_width"] == pytest.approx(0.4, abs=0.02)
    assert peak_y / single["grid_height"] == pytest.approx(0.45, abs=0.02)
    assert matrix.sum() == pytest.approx(1, abs=1e-5)
    assert single["included_observations"] == 1

    doubled = _aggregate([_frame(1, 1, [_obs(0.4, 0.45)]), _frame(2, 2, [_obs(0.4, 0.45)])])
    assert doubled["total_weight"] == pytest.approx(2)
    assert doubled["max_value"] > single["max_value"]

    empty_but_processed = _aggregate([_frame(1, 1)])
    assert empty_but_processed["missing_data"] is False
    assert set(empty_but_processed["values"]) == {0.0}
    no_samples = _aggregate([])
    assert no_samples["missing_data"] is True


def test_filters_time_boundaries_and_timeline_covered_empty_bins() -> None:
    frames = [
        _frame(1, 0, [_obs(0.2, 0.3, "car")]),
        _frame(2, 5, [_obs(0.3, 0.4, "truck")]),
        _frame(3, 9.9, [_obs(0.4, 0.5, "car")]),
        _frame(4, 10.1, [_obs(0.5, 0.6, "car")]),
        _frame(5, 15),
    ]
    result = heatmap(
        frames,
        width=1050,
        height=589,
        crop={"x": 0, "y": 0, "width": 1, "height": 1},
        duration_s=20,
        sample_fps=1,
        start_s=5,
        end_s=10,
        classes={"car"},
    )
    assert result["included_observations"] == 1
    assert result["observation_totals_by_class"] == {"car": 1}
    series = timeline(frames, duration_s=20, sample_fps=1, start_s=0, end_s=10, bin_seconds=5)
    assert [item["sampled_frames"] for item in series["bins"]] == [1, 2]
    assert series["bins"][0]["observations_by_class"] == {"car": 1}
    assert series["bins"][1]["observations_by_class"] == {"truck": 1, "car": 1}


def test_presence_seconds_is_cadence_resistant_and_does_not_fill_long_gaps() -> None:
    slow = [_frame(i + 1, float(i), [_obs(0.4, 0.45)]) for i in range(6)]
    fast = [_frame(i + 1, i / 2, [_obs(0.4, 0.45)]) for i in range(12)]

    def run(frames, sample_fps):
        return heatmap(
            frames,
            width=1050,
            height=589,
            crop={"x": 0, "y": 0, "width": 1, "height": 1},
            duration_s=10,
            sample_fps=sample_fps,
            start_s=0,
            end_s=10,
            mode="presence_seconds",
        )

    assert run(slow, 1)["total_weight"] == pytest.approx(run(fast, 2)["total_weight"])
    gap = run([_frame(1, 0, [_obs(0.4, 0.45)]), _frame(2, 9, [_obs(0.4, 0.45)])], 1)
    assert gap["total_weight"] == pytest.approx(1)


def test_invalid_rows_modes_and_numerical_extremes_are_rejected() -> None:
    with pytest.raises(ValueError, match="pts"):
        validate_frame_record(_frame(1, math.nan), duration_s=20)
    with pytest.raises(ValueError, match="time_range"):
        _aggregate([], start_s=12, end_s=12)
    with pytest.raises(ValueError, match="classes"):
        _aggregate([], classes={"person"})
    with pytest.raises(ValueError, match="radius"):
        _aggregate([], radius=math.inf)
