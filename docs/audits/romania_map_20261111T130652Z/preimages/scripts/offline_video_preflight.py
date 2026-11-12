"""Decode and run the installed YOLOX-S ONNX detector on real frames from the two local files.

Artifacts are written only below ignored ``data/offline-analysis/preflight``. Originals are
opened read-only. No network, W&B, or remote inference is used.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
from roadsentinel.detector import COCO, YoloXOnnx

INPUTS = (
    Path("/home/justin7m8/Videos/RoadSentinel/Screencast from 2026-11-08 00-05-47.webm"),
    Path("/home/justin7m8/Videos/RoadSentinel/Screencast from 2026-11-08 00-20-53.webm"),
)
OUT = ROOT / "data/offline-analysis/preflight"


def probe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,r_frame_rate,avg_frame_rate:format=duration,size",
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
    stream.update(info.get("format", {}))
    return stream


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def draw(frame: np.ndarray, detections, pts_s: float) -> np.ndarray:
    output = frame.copy()
    for box, score, class_id in zip(detections.xyxy, detections.confidence, detections.class_id):
        x1, y1, x2, y2 = (round(v) for v in box)
        label = f"{COCO.get(int(class_id), str(int(class_id)))} {float(score):.2f}"
        cv2.rectangle(output, (x1, y1), (x2, y2), (40, 220, 125), 2)
        cv2.putText(
            output, label, (x1, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (40, 220, 125), 2, cv2.LINE_AA
        )
    cv2.rectangle(output, (0, 0), (output.shape[1], 30), (10, 10, 10), -1)
    cv2.putText(
        output,
        f"RECORDED ANALYSIS · PTS {pts_s:.2f}s",
        (10, 21),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (245, 245, 245),
        1,
        cv2.LINE_AA,
    )
    return output


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    detector = YoloXOnnx(ROOT / "models/yolox_s.onnx", input_size=640)
    output = {
        "model": "YOLOX-S ONNX",
        "model_sha256": hashlib.sha256((ROOT / "models/yolox_s.onnx").read_bytes()).hexdigest(),
        "provider": detector.provider,
        "files": [],
    }
    for path in INPUTS:
        metadata = probe(path)
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise RuntimeError(f"OpenCV/FFmpeg cannot decode {path.name}")
        duration = float(metadata["duration"])
        points = sorted({1.0, duration * 0.25, duration * 0.5, duration * 0.75, duration - 5.0})
        samples = []
        frames_small = []
        detections_total = 0
        inference_times = []
        for index, pts in enumerate(points):
            capture.set(cv2.CAP_PROP_POS_MSEC, pts * 1000)
            ok, frame = capture.read()
            if not ok or frame is None:
                # Some WebM indexes seek a few seconds before EOF; retry farther from the end.
                retry_pts = max(0.0, min(pts - 3.0, duration - 8.0))
                capture.set(cv2.CAP_PROP_POS_MSEC, retry_pts * 1000)
                ok, frame = capture.read()
                if not ok or frame is None:
                    raise RuntimeError(f"failed to decode {path.name} near EOF ({pts:.2f}s)")
            actual_pts = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
            start = time.perf_counter()
            detections = detector.predict(frame, classes={1, 2, 3, 5, 7})
            inference_s = time.perf_counter() - start
            inference_times.append(inference_s)
            detections_total += len(detections.class_id)
            samples.append(
                {
                    "requested_pts_s": pts,
                    "decoded_pts_s": actual_pts,
                    "size": [int(frame.shape[1]), int(frame.shape[0])],
                    "detection_count": len(detections.class_id),
                    "classes": [COCO.get(int(v), str(int(v))) for v in detections.class_id],
                    "inference_s": round(inference_s, 4),
                }
            )
            annotated = draw(frame, detections, actual_pts)
            sample_path = OUT / f"{path.stem[:20]}-sample-{index + 1}.jpg"
            cv2.imwrite(str(sample_path), annotated, [cv2.IMWRITE_JPEG_QUALITY, 82])
            thumb = cv2.resize(annotated, (700, 393))
            frames_small.append(thumb)
        capture.release()
        # Decode a short 2 Hz source sample to estimate how often screen content changes.
        cadence_cap = cv2.VideoCapture(str(path))
        cadence_hashes = []
        for second in range(min(31, int(duration))):
            cadence_cap.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
            ok, frame = cadence_cap.read()
            if not ok:
                continue
            reduced = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
            cadence_hashes.append(hashlib.sha256(reduced.tobytes()).hexdigest())
        cadence_cap.release()
        distinct = sum(a != b for a, b in itertools.pairwise(cadence_hashes))
        contact = np.vstack(
            (np.hstack(frames_small[:3]), np.hstack(frames_small[3:] + [np.zeros_like(frames_small[0])]))
        )
        cv2.imwrite(str(OUT / f"{path.stem[:20]}-contact.jpg"), contact, [cv2.IMWRITE_JPEG_QUALITY, 82])
        output["files"].append(
            {
                "filename": path.name,
                "sha256": file_hash(path),
                "metadata": metadata,
                "model_samples": samples,
                "sample_detection_observations": detections_total,
                "median_inference_fps": round(1 / float(np.median(inference_times)), 3),
                "screen_content_changes_across_1s_samples": distinct,
                "screen_sample_count": len(cadence_hashes),
                "artifacts": f"data/offline-analysis/preflight/{path.stem[:20]}-*.jpg",
            }
        )
    report = json.dumps(output, ensure_ascii=False, indent=2)
    (OUT / "preflight.json").write_text(report + "\n", encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
