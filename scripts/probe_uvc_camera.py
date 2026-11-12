"""Bounded, non-recording diagnostic for one explicitly selected local UVC camera."""

import argparse
import hashlib
import sys
import time
from itertools import pairwise
from pathlib import Path

import cv2

# Make the documented direct-script invocation work from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from roadsentinel.sources import SourceError, SourceSpec, open_capture


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-index", type=int, required=True, choices=range(16))
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--fourcc", choices=("auto", "MJPG", "YUYV"), default="auto")
    parser.add_argument("--width", type=int, choices=(320, 640, 1280, 1920))
    parser.add_argument("--height", type=int, choices=(240, 480, 720, 1080))
    args = parser.parse_args()
    if not 1 <= args.seconds <= 15:
        parser.error("--seconds must be between 1 and 15")

    capture = None
    started = time.monotonic()
    stamps: list[float] = []
    hashes: set[str] = set()
    dimensions = None
    try:
        capture = open_capture(SourceSpec.from_camera({"video": f"device:{args.device_index}"}))
        if args.fourcc != "auto":
            capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*args.fourcc))
        if args.width and args.height:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        while time.monotonic() - started < args.seconds:
            ok, frame = capture.read()
            now = time.monotonic()
            if not ok or frame is None:
                continue
            stamps.append(now)
            dimensions = [int(frame.shape[1]), int(frame.shape[0])]
            tiny = cv2.resize(frame, (32, 18), interpolation=cv2.INTER_AREA)
            hashes.add(hashlib.sha256(tiny.tobytes()).hexdigest())
    except SourceError as exc:
        print(f"CAMERA_UNAVAILABLE: {exc}")
        return 2
    finally:
        if capture is not None:
            capture.release()

    elapsed = time.monotonic() - started
    intervals = [b - a for a, b in pairwise(stamps) if b > a]
    fps = (len(intervals) / sum(intervals)) if intervals else 0.0
    print(
        f"device_index={args.device_index} duration_s={elapsed:.2f} frames={len(stamps)} "
        f"requested_fourcc={args.fourcc} requested_dimensions="
        f"{args.width}x{args.height} actual_dimensions={dimensions} "
        f"distinct_sample_hashes={len(hashes)} observed_fps={fps:.2f} "
        f"fresh_frame_changes={'yes' if len(hashes) > 1 else 'no'}"
    )
    return 0 if len(stamps) >= 2 and len(hashes) > 1 else 3


if __name__ == "__main__":
    raise SystemExit(main())
