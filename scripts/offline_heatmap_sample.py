"""Run a bounded real YOLOX/heatmap sample on one local recording (no writes/network)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import cv2
from app.services.offline_heatmap import heatmap, observation_from_roi

from roadsentinel.detector import COCO, YoloXOnnx


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metadata(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    info = json.loads(result.stdout)
    stream = info["streams"][0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "duration_s": float(info["format"]["duration"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="local authorized recording")
    parser.add_argument("--model", type=Path, default=Path("models/yolox_s.onnx"))
    args = parser.parse_args()
    video = args.video.resolve(strict=True)
    model_path = args.model.resolve(strict=True)
    info = metadata(video)
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise SystemExit("OpenCV/FFmpeg could not open the local recording")
    detector = YoloXOnnx(model_path, input_size=640)
    times = sorted({1.0, info["duration_s"] / 2, info["duration_s"] - 5.0})
    samples = []
    summaries = []
    try:
        for sequence, requested_pts in enumerate(times, 1):
            capture.set(cv2.CAP_PROP_POS_MSEC, requested_pts * 1000)
            ok, frame = capture.read()
            if not ok or frame is None:
                raise SystemExit(f"Could not decode frame near PTS {requested_pts:.3f}s")
            pts = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
            width, height = int(frame.shape[1]), int(frame.shape[0])
            if (width, height) != (info["width"], info["height"]):
                raise SystemExit("Decoded frame dimensions differ from ffprobe metadata")
            detections = detector.predict(frame, classes={1, 2, 3, 5, 7})
            observations = []
            for box, confidence, class_id in zip(
                detections.xyxy, detections.confidence, detections.class_id, strict=True
            ):
                observation = observation_from_roi(
                    box=box,
                    class_id=int(class_id),
                    class_name=COCO.get(int(class_id), "other"),
                    confidence=float(confidence),
                    track_id=None,
                    crop_px=(0, 0, width, height),
                    source_width=width,
                    source_height=height,
                )
                if observation:
                    observations.append(observation)
            samples.append(
                {
                    "record_type": "sample",
                    "schema_version": 1,
                    # Seeking does not expose a reliable original frame index; this is the
                    # monotonic spot-sample index required by the analytics schema.
                    "source_frame_index": sequence - 1,
                    "sample_sequence": sequence,
                    "pts_seconds": pts,
                    "observations": observations,
                }
            )
            summaries.append(
                {
                    "pts_s": round(pts, 3),
                    "vehicle_observations": len(observations),
                    "classes": {
                        name: sum(row["class_name"] == name for row in observations)
                        for name in ("car", "truck", "bus", "motorcycle", "bicycle")
                    },
                }
            )
    finally:
        capture.release()

    result = heatmap(
        samples,
        width=info["width"],
        height=info["height"],
        crop={"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
        duration_s=info["duration_s"],
        sample_fps=0.5,
        start_s=0.0,
        end_s=info["duration_s"],
        grid_width=128,
        radius=0.03,
    )
    print(
        json.dumps(
            {
                "source_kind": "RECORDED SCREENCAST",
                "filename": video.name,
                "sha256": file_sha256(video),
                **info,
                "model": model_path.name,
                "model_sha256": file_sha256(model_path),
                "provider": detector.provider,
                "samples": summaries,
                "sampled_vehicle_observations": result["included_observations"],
                "heatmap_total_weight": result["total_weight"],
                "heatmap_nonzero_cells": sum(value > 0 for value in result["values"]),
                "scope": "three full-frame spot samples; no crop, tracker continuity, persistence, or browser claim",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
