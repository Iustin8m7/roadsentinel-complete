"""Run one bounded, non-recording YOLOX pass on the configured Ilișești live snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from roadsentinel.detector import COCO, YoloXOnnx
from roadsentinel.sources import SourceSpec, open_capture

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "cameras/ilisesti-dn17.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    cfg = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))
    spec = SourceSpec.from_camera(cfg)  # verifies the private source-specific attestation
    capture = open_capture(spec)
    try:
        started = time.perf_counter()
        ok, frame = capture.read()
        capture_s = time.perf_counter() - started
        if not ok or frame is None:
            reason = getattr(capture, "last_error", None) or "no new fresh provider snapshot"
            print(json.dumps({"camera": cfg["id"], "result": "no_fresh_snapshot", "reason": reason}))
            return 3
        model_path = ROOT / cfg["model"]
        model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
        detector = YoloXOnnx(model_path, input_size=640)
        inference_started = time.perf_counter()
        detections = detector.predict(
            frame,
            classes={1, 2, 3, 5, 7},
            confidence_threshold=float(cfg["model_confidence"]),
            iou_threshold=float(cfg["model_iou_threshold"]),
        )
        elapsed = time.perf_counter() - inference_started
        version = getattr(capture, "version", None)
        modified_at = getattr(capture, "last_modified_at", None)
        print(json.dumps({
            "camera": "Ilișești DN17",
            "result": "real_source_snapshot_inferred",
            "source_kind": "provider_refreshed_jpeg_snapshot",
            "source_version": list(version) if version else None,
            "source_last_modified_utc": modified_at.isoformat() if modified_at else None,
            "observed_at_utc": datetime.now(UTC).isoformat(),
            "dimensions": {"width": int(frame.shape[1]), "height": int(frame.shape[0])},
            "capture_seconds": round(capture_s, 4),
            "inference_seconds": round(elapsed, 4),
            "inference_fps": round(1 / elapsed, 3) if elapsed else None,
            "model": "YOLOX-S ONNX",
            "model_sha256": model_hash,
            "provider": detector.provider,
            "provider_fallback_reason": detector.provider_fallback_reason,
            "vehicle_detection_count": len(detections.class_id),
            "vehicle_class_counts": dict(Counter(
                COCO.get(int(class_id), str(int(class_id))) for class_id in detections.class_id
            )),
            "retained_media": False,
            "processed_frames": 1,
        }, ensure_ascii=False))
        return 0
    finally:
        capture.release()


if __name__ == "__main__":
    raise SystemExit(main())
