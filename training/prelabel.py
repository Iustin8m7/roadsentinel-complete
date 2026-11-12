"""Pre-label sampled frames with the current detector (YOLO txt next to each image).

Annotators then only correct boxes instead of drawing them from scratch.
Usage: python training/prelabel.py [--model yolo11m.pt] [--conf 0.35] [--device mps]
"""
import argparse
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent
ROAD_CLASSES = [0, 1, 2, 3, 5, 7]  # person, bicycle, car, motorcycle, bus, truck


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default=str(ROOT / "training" / "frames"))
    ap.add_argument("--model", default="yolo11s.pt")
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--device", default=None, help="e.g. mps, 0, cpu (default: ultralytics picks)")
    a = ap.parse_args()
    model = YOLO(a.model)
    images = sorted(Path(a.frames).rglob("*.jpg"))
    if not images:
        raise SystemExit("No frames found. Run training/extract_frames.py first.")
    # A list source is run as one batch, so feed it in small chunks to bound memory.
    for i in range(0, len(images), a.batch):
        chunk = [str(p) for p in images[i:i + a.batch]]
        for r in model.predict(chunk, stream=True, conf=a.conf, imgsz=a.imgsz,
                               classes=ROAD_CLASSES, device=a.device, verbose=False):
            lines = [f"{int(c)} {x:.6f} {y:.6f} {w:.6f} {h:.6f}"
                     for c, (x, y, w, h) in zip(r.boxes.cls.tolist(), r.boxes.xywhn.tolist())]
            Path(r.path).with_suffix(".txt").write_text("\n".join(lines) + ("\n" if lines else ""))
    print(f"Pre-labeled {len(images)} frames in {a.frames}")


if __name__ == "__main__":
    main()
