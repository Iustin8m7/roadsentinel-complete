#!/usr/bin/env python3
"""Prepare small licensed browser inputs; no downloads or existing-file replacement."""

import hashlib
import json
import subprocess
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/tmp/Street_traffic.webm")
SOURCE_SHA = "e5facb24baf755f0c1193999d823e99f6032661ad2bdef5cc28cc1cbbfde03e2"


def digest(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def main():
    if ROOT != Path("/home/justin7m8/Documents/roadsentinel-integration"):
        raise SystemExit("Unexpected integration workspace")
    if not SOURCE.is_file() or digest(SOURCE) != SOURCE_SHA:
        raise SystemExit("Required licensed local source missing/different; no download attempted")
    folder = ROOT / "data/integration-browser-fixtures"
    folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    if folder.resolve() != folder or folder.is_symlink():
        raise SystemExit("Fixture path must remain inside the integration workspace")
    manifest = folder / "manifest.json"
    if manifest.exists():
        previous = json.loads(manifest.read_text())
        if previous.get("source_sha256") != SOURCE_SHA or not all(
            (folder / item["name"]).is_file()
            and digest(folder / item["name"]) == item["sha256"]
            for item in previous["outputs"]
        ):
            raise SystemExit("Existing fixture manifest/content differs; no replacement allowed")
        print("Verified existing fixtures:", folder)
        return
    moving = folder / "LICENSED_MOVING_TRAFFIC.mp4"
    frozen = folder / "SYNTHETIC_TEST_frozen_licensed_frame.mp4"
    if moving.exists() or frozen.exists():
        raise SystemExit("Partial existing fixtures preserved; choose a new owned folder")
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-n", "-i", str(SOURCE), "-t", "30",
         "-vf", "fps=10,scale=960:540", "-an", "-c:v", "libx264", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", str(moving)], check=True, timeout=60,
    )
    cap = cv2.VideoCapture(str(SOURCE))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit("Licensed source could not be decoded")
    writer = cv2.VideoWriter(str(frozen), cv2.VideoWriter_fourcc(*"mp4v"), 5, (640, 360))
    if not writer.isOpened():
        raise SystemExit("Synthetic fixture encoder unavailable")
    for _ in range(180):
        writer.write(cv2.resize(frame, (640, 360)))
    writer.release()
    records = []
    for file in (moving, frozen):
        file.chmod(0o600)
        records.append({"name": file.name, "sha256": digest(file), "bytes": file.stat().st_size})
    manifest.write_text(json.dumps({
        "source": "https://commons.wikimedia.org/wiki/File:Street_traffic.webm",
        "author": "Editor", "license": "CC BY 3.0", "source_sha256": SOURCE_SHA,
        "moving": "30 seconds, 300 frames, 10 FPS, real moving traffic; no accuracy labels",
        "synthetic": "36 seconds, 180 repeated frames; SYNTHETIC TEST, never a real incident",
        "outputs": records,
    }, indent=2))
    manifest.chmod(0o600)
    print("Prepared licensed moving and explicitly synthetic inputs:", folder)


if __name__ == "__main__":
    main()
