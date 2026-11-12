"""Sample frames from raw clips into training/frames/ for labeling.

Pass video files explicitly and/or a --src directory to scan. Pipeline output (anything under a
`media/` dir, or files named `annotated*` / `event_*`) is skipped: those frames carry drawn boxes or
blurred plates and must never become training data. --start/--end (seconds) keep a segment of each
clip, so a held-out test segment can be extracted separately and excluded from training.

Usage:
  python training/extract_frames.py data/videos/vehicles.mp4 --step 2 --width 1280
  python training/extract_frames.py --src data --every 2
  python training/extract_frames.py data/videos/vehicles-2.mp4 --start 30 --out training/frames-test
"""
import argparse
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
VIDEO_EXT = {".mp4", ".webm", ".avi", ".mkv", ".mov"}


def is_raw(p: Path) -> bool:
    return (p.suffix.lower() in VIDEO_EXT and "media" not in p.parts
            and not p.name.startswith(("annotated", "event_")))


def extract(video: Path, out: Path, step: int | None, every_s: float, width: int,
            start: float, end: float | None) -> int:
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    step = step or max(1, round(fps * every_s))
    first = round(start * fps)
    last = round(end * fps) if end is not None else None
    out.mkdir(parents=True, exist_ok=True)
    i = saved = 0
    while cap.grab():
        if last is not None and i >= last:
            break
        if i >= first and (i - first) % step == 0:
            ok, frame = cap.retrieve()
            if ok:
                h, w = frame.shape[:2]
                if w > width:
                    frame = cv2.resize(frame, (width, round(h * width / w)), interpolation=cv2.INTER_AREA)
                cv2.imwrite(str(out / f"{video.stem}_{i:07d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
                saved += 1
        i += 1
    cap.release()
    return saved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="*", help="video files to sample")
    ap.add_argument("--src", help="directory to scan recursively for videos")
    ap.add_argument("--out", default=str(ROOT / "training" / "frames"))
    ap.add_argument("--every", type=float, default=2.0, help="seconds between sampled frames")
    ap.add_argument("--step", type=int, help="sample every Nth frame (overrides --every)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--start", type=float, default=0.0, help="first second to sample")
    ap.add_argument("--end", type=float, help="stop before this second")
    a = ap.parse_args()
    if not a.videos and not a.src:
        a.src = str(ROOT / "data")

    candidates = [Path(v) for v in a.videos]
    if a.src:
        candidates += sorted(Path(a.src).rglob("*"))
    videos = []
    for v in candidates:
        if not is_raw(v.resolve()):
            if v.suffix.lower() in VIDEO_EXT:
                print(f"skip {v} (pipeline output)")
            continue
        if v not in videos:
            videos.append(v)
    if not videos:
        raise SystemExit("No raw videos found. Run scripts/download_data.sh first.")
    for v in videos:
        n = extract(v, Path(a.out) / v.parent.name, a.step, a.every, a.width, a.start, a.end)
        print(f"{v.name}: {n} frames")


if __name__ == "__main__":
    main()
