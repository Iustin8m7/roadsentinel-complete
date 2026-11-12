"""Evaluate detector weights on the held-out test split of training/dataset.yaml.

Usage: python training/evaluate.py yolo11s.pt training/runs/detect/<name>/weights/best.pt
"""
import argparse
from pathlib import Path

from ultralytics import YOLO

from train import HERE, resolve_data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("weights", nargs="+")
    ap.add_argument("--data", default=str(HERE / "dataset.yaml"))
    ap.add_argument("--imgsz", type=int, default=960)
    ap.add_argument("--device", default="mps")
    a = ap.parse_args()
    data = resolve_data(a.data)
    for w in a.weights:
        m = YOLO(w).val(data=data, split="test", imgsz=a.imgsz, batch=4, device=a.device,
                        project=str(HERE / "runs" / "eval"), name=Path(w).stem, plots=False)
        print(f"\n{w}: mAP50 {m.box.map50:.4f}  mAP50-95 {m.box.map:.4f}")
        for i, c in enumerate(m.box.ap_class_index):
            print(f"  {m.names[int(c)]:<10} mAP50 {m.box.ap50[i]:.4f}  mAP50-95 {m.box.ap[i]:.4f}")


if __name__ == "__main__":
    main()
