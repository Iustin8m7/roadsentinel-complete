"""Deterministic aggregation of YOLOX/ByteTrack observations from completed recordings.

Coordinates are normalized against the original source frame. Density is a count of detector
observations, not vehicles or traffic flow. Presence seconds are sampled estimates, never physical
road occupancy; time coverage is capped to avoid filling long gaps.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Iterator
from typing import Any, Literal

import cv2
import numpy as np

HEATMAP_SCHEMA_VERSION = 1
VEHICLE_CLASSES = ("bicycle", "car", "motorcycle", "bus", "truck")
MAX_HEATMAP_CELLS = 65_536
MAX_TIMELINE_BINS = 400
MAX_ARTIFACT_BYTES = 128 * 1024 * 1024
HeatmapMode = Literal["observations", "presence_seconds"]


def observation_from_roi(
    *,
    box: Iterable[float],
    class_id: int,
    class_name: str,
    confidence: float,
    track_id: int | None,
    crop_px: tuple[int, int, int, int],
    source_width: int,
    source_height: int,
) -> dict[str, Any] | None:
    """Map one detector ROI box exactly once to normalized full-source coordinates."""
    if class_name not in VEHICLE_CLASSES:
        return None
    values = np.asarray(tuple(box), dtype=np.float64)
    if values.shape != (4,) or not np.isfinite(values).all():
        return None
    if not math.isfinite(confidence) or not 0 <= confidence <= 1:
        return None
    left, top, width, height = crop_px
    if min(source_width, source_height, width, height) <= 0 or left < 0 or top < 0:
        return None
    x1, y1, x2, y2 = values
    x1, x2 = np.clip((x1 + left, x2 + left), 0, source_width)
    y1, y2 = np.clip((y1 + top, y2 + top), 0, source_height)
    if x2 <= x1 or y2 <= y1:
        return None
    return {
        "class_id": int(class_id),
        "class_name": class_name,
        "confidence": float(confidence),
        "bbox_normalized": [
            float(x1 / source_width),
            float(y1 / source_height),
            float(x2 / source_width),
            float(y2 / source_height),
        ],
        "anchor_normalized": [float((x1 + x2) / (2 * source_width)), float(y2 / source_height)],
        "track_id": int(track_id) if track_id is not None else None,
    }


def validate_frame_record(record: dict[str, Any], *, duration_s: float) -> dict[str, Any]:
    pts = record.get("pts_seconds")
    if not isinstance(pts, (float, int)) or not math.isfinite(pts) or pts < 0:
        raise ValueError("invalid_observation_pts")
    if pts > duration_s + 2:
        raise ValueError("observation_pts_out_of_range")
    sequence = record.get("sample_sequence")
    frame_index = record.get("source_frame_index")
    observations = record.get("observations")
    if (
        not isinstance(sequence, int)
        or sequence < 1
        or not isinstance(frame_index, int)
        or frame_index < 0
    ):
        raise ValueError("invalid_observation_sequence")
    if not isinstance(observations, list):
        raise ValueError("invalid_observation_rows")
    clean = []
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        anchor = observation.get("anchor_normalized")
        bbox = observation.get("bbox_normalized")
        confidence = observation.get("confidence")
        name = observation.get("class_name")
        if (
            name not in VEHICLE_CLASSES
            or not isinstance(anchor, list)
            or len(anchor) != 2
            or not isinstance(bbox, list)
            or len(bbox) != 4
            or not isinstance(confidence, (float, int))
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            continue
        numeric = [*anchor, *bbox]
        if not all(isinstance(v, (float, int)) and math.isfinite(v) for v in numeric):
            continue
        if not (0 <= anchor[0] <= 1 and 0 <= anchor[1] <= 1):
            continue
        if not (0 <= bbox[0] < bbox[2] <= 1 and 0 <= bbox[1] < bbox[3] <= 1):
            continue
        clean.append(observation)
    return {**record, "pts_seconds": float(pts), "observations": clean}


def weighted_frames(
    frames: Iterable[dict[str, Any]], *, sample_fps: float, max_gap_s: float = 2.5
) -> Iterator[tuple[dict[str, Any], float]]:
    """Yield each sample with capped forward coverage; repeated/nonmonotone PTS gets zero weight."""
    iterator = iter(frames)
    try:
        current = next(iterator)
    except StopIteration:
        return
    nominal = min(max(1 / max(sample_fps, 0.01), 0), max_gap_s)
    for following in iterator:
        delta = float(following["pts_seconds"]) - float(current["pts_seconds"])
        coverage = delta if 0 < delta <= max_gap_s else 0.0
        yield current, coverage
        current = following
    yield current, nominal


def _in_interval(pts: float, start_s: float, end_s: float, duration_s: float) -> bool:
    return start_s <= pts < end_s or (end_s >= duration_s and pts == duration_s)


def _grid_shape(width: int, height: int, grid_width: int) -> tuple[int, int]:
    if width <= 0 or height <= 0 or grid_width < 16 or grid_width > 256:
        raise ValueError("invalid_heatmap_dimensions")
    grid_height = max(16, min(256, round(grid_width * height / width)))
    if grid_width * grid_height > MAX_HEATMAP_CELLS:
        raise ValueError("heatmap_grid_too_large")
    return grid_width, grid_height


def heatmap(
    frames: Iterable[dict[str, Any]],
    *,
    width: int,
    height: int,
    crop: dict[str, float],
    duration_s: float,
    sample_fps: float,
    start_s: float,
    end_s: float,
    classes: set[str] | None = None,
    mode: HeatmapMode = "observations",
    grid_width: int = 128,
    radius: float = 0.03,
) -> dict[str, Any]:
    if mode not in {"observations", "presence_seconds"}:
        raise ValueError("unsupported_heatmap_mode")
    if not (math.isfinite(start_s) and math.isfinite(end_s) and 0 <= start_s < end_s <= duration_s):
        raise ValueError("invalid_time_range")
    if not math.isfinite(radius) or not 0.005 <= radius <= 0.12:
        raise ValueError("invalid_heatmap_radius")
    selected = set(VEHICLE_CLASSES if classes is None else classes)
    if not selected or not selected.issubset(VEHICLE_CLASSES):
        raise ValueError("invalid_vehicle_classes")
    gw, gh = _grid_shape(width, height, grid_width)
    matrix = np.zeros((gh, gw), dtype=np.float64)
    samples = 0
    observation_count = 0
    class_totals: Counter[str] = Counter()
    total_weight = 0.0
    excluded_gap_samples = 0
    source_iter = weighted_frames(frames, sample_fps=sample_fps)
    for frame, coverage in source_iter:
        pts = float(frame["pts_seconds"])
        if not _in_interval(pts, start_s, end_s, duration_s):
            continue
        samples += 1
        if coverage == 0:
            excluded_gap_samples += 1
        frame_weight = 1.0 if mode == "observations" else min(coverage, max(0.0, end_s - pts))
        for obs in frame["observations"]:
            name = obs["class_name"]
            if name not in selected:
                continue
            ax, ay = obs["anchor_normalized"]
            if not (
                crop["x"] <= ax <= crop["x"] + crop["width"]
                and crop["y"] <= ay <= crop["y"] + crop["height"]
            ):
                continue
            observation_count += 1
            class_totals[name] += 1
            if frame_weight > 0:
                ix = min(gw - 1, max(0, int(float(ax) * gw)))
                iy = min(gh - 1, max(0, int(float(ay) * gh)))
                matrix[iy, ix] += frame_weight
                total_weight += frame_weight

    if total_weight:
        sigma = max(0.65, radius * gw)
        matrix = cv2.GaussianBlur(
            matrix, (0, 0), sigmaX=sigma, sigmaY=sigma, borderType=cv2.BORDER_REFLECT
        )
        yy, xx = np.mgrid[0:gh, 0:gw]
        nx, ny = (xx + 0.5) / gw, (yy + 0.5) / gh
        mask = (
            (nx >= crop["x"])
            & (nx <= crop["x"] + crop["width"])
            & (ny >= crop["y"])
            & (ny <= crop["y"] + crop["height"])
        )
        matrix *= mask
        if matrix.sum() > 0:
            matrix *= total_weight / matrix.sum()
    return {
        "mode": mode,
        "grid_width": gw,
        "grid_height": gh,
        "values": matrix.astype(np.float32).ravel().tolist(),
        "min_value": float(matrix.min()) if matrix.size else 0.0,
        "max_value": float(matrix.max()) if matrix.size else 0.0,
        "total_weight": total_weight,
        "normalization": "per_filter_max",
        "coordinate_reference": "normalized_full_source_frame; row-major y,x",
        "image_width": width,
        "image_height": height,
        "crop": crop,
        "filter_start_s": start_s,
        "filter_end_s": end_s,
        "included_classes": sorted(selected),
        "included_observations": observation_count,
        "processed_samples": samples,
        "partial": False,
        "missing_data": samples == 0,
        "excluded_gap_samples": excluded_gap_samples,
        "observation_totals_by_class": dict(class_totals),
        "warnings": [
            "Per-filter intensity scale is recomputed for the selected class and time range.",
            "Observations are not unique vehicles, validated volume, speed, or road occupancy.",
            "Estimated presence seconds use capped intervals between sampled media PTS values.",
        ]
        + (
            [
                f"{excluded_gap_samples} intervals had duplicate PTS or gaps over 2.5 s; "
                "they receive no presence weight."
            ]
            if excluded_gap_samples
            else []
        ),
        "algorithm_version": HEATMAP_SCHEMA_VERSION,
    }


def timeline(
    frames: Iterable[dict[str, Any]],
    *,
    duration_s: float,
    sample_fps: float,
    start_s: float,
    end_s: float,
    classes: set[str] | None = None,
    bin_seconds: float = 5,
) -> dict[str, Any]:
    if not (math.isfinite(start_s) and math.isfinite(end_s) and 0 <= start_s < end_s <= duration_s):
        raise ValueError("invalid_time_range")
    if not math.isfinite(bin_seconds) or not 1 <= bin_seconds <= 300:
        raise ValueError("invalid_timeline_bin")
    selected = set(VEHICLE_CLASSES if classes is None else classes)
    if not selected or not selected.issubset(VEHICLE_CLASSES):
        raise ValueError("invalid_vehicle_classes")
    count = min(MAX_TIMELINE_BINS, max(1, math.ceil((end_s - start_s) / bin_seconds)))
    actual_bin = (end_s - start_s) / count
    bins = [
        {
            "start_s": start_s + i * actual_bin,
            "end_s": start_s + (i + 1) * actual_bin,
            "observations_by_class": {},
            "vehicle_seconds_by_class": {},
            "sampled_frames": 0,
            "coverage_flag": "no_samples",
        }
        for i in range(count)
    ]
    excluded_gap_samples = 0
    for frame, coverage in weighted_frames(frames, sample_fps=sample_fps):
        pts = float(frame["pts_seconds"])
        if not _in_interval(pts, start_s, end_s, duration_s):
            continue
        if coverage == 0:
            excluded_gap_samples += 1
        index = min(count - 1, int((pts - start_s) / actual_bin))
        current = bins[index]
        current["sampled_frames"] += 1
        for obs in frame["observations"]:
            name = obs["class_name"]
            if name not in selected:
                continue
            current["observations_by_class"][name] = (
                current["observations_by_class"].get(name, 0) + 1
            )
            presence = min(coverage, max(0.0, end_s - pts))
            if presence:
                current["vehicle_seconds_by_class"][name] = (
                    current["vehicle_seconds_by_class"].get(name, 0.0) + presence
                )
        current["coverage_flag"] = (
            "covered_with_observations" if current["observations_by_class"] else "covered_empty"
        )
    return {
        "source_duration_s": duration_s,
        "filter_start_s": start_s,
        "filter_end_s": end_s,
        "bin_seconds": actual_bin,
        "included_classes": sorted(selected),
        "bins": bins,
        "partial": False,
        "warnings": [
            "Y-axis values are detector observations, not validated traffic counts.",
            "Vehicle-seconds are sampled visual presence estimates with gaps capped or excluded.",
            "Bins without processed samples are distinct from processed bins with zero detections.",
        ]
        + (
            [
                f"{excluded_gap_samples} intervals had duplicate PTS or gaps over 2.5 s; "
                "they receive no presence weight."
            ]
            if excluded_gap_samples
            else []
        ),
        "algorithm_version": HEATMAP_SCHEMA_VERSION,
    }
