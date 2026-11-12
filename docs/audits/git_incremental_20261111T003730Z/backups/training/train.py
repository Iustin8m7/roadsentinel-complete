"""Fine-tune YOLO11 on training/dataset.yaml.

Defaults fit a 4 GB laptop GPU (RTX 3050): yolo11s, 960 px, batch 4, mixed precision.
Usage: python training/train.py [--model yolo11s.pt] [--epochs 80] [--imgsz 960] [--batch 4] [--name rs-v1]
"""
import os
import argparse
from pathlib import Path

import torch
import wandb
import yaml
from ultralytics import YOLO, settings

HERE = Path(__file__).resolve().parent


def resolve_data(data: str) -> str:
    """Write a copy of the dataset yaml with an absolute `path:`.

    Ultralytics resolves a relative `path:` against its global datasets_dir, not the yaml's folder,
    so the relative path in dataset.yaml is anchored to the yaml location here instead.
    """
    src = Path(data).resolve()
    cfg = yaml.safe_load(src.read_text())
    root = Path(cfg.get("path", "."))
    if not root.is_absolute():
        root = (src.parent / root).resolve()
    cfg["path"] = str(root)
    out = root / f"{src.stem}.resolved.yaml"
    root.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return str(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="yolo11s.pt")
    ap.add_argument("--data", default=str(HERE / "dataset.yaml"))
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--imgsz", type=int, default=960)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--freeze", type=int, help="freeze the first N layers (10 = the YOLO11 backbone)")
    ap.add_argument("--name", help="run name (default: rs-<model>-<imgsz>px-e<epochs>-<device>)")
    ap.add_argument("--wandb-project", default="RoadSentinel")
    a = ap.parse_args()

    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = 0
    else:
        device = "cpu"
    print("Training on", {"mps": "Apple MPS", 0: "CUDA"}.get(device, "CPU (slow)"))
    name = a.name or f"rs-{Path(a.model).stem}-{a.imgsz}px-e{a.epochs}-{device if device != 0 else 'cuda'}"

    # Ultralytics' W&B callback uses args.project as the W&B project, but args.project is our local
    # runs folder. Starting the run here makes the callback reuse it instead of creating its own.
    # Training frames are raw footage: W&B (which uploads sample images) is opt-in.
    track = os.environ.get("RS_EXPERIMENT_TRACKING", "off") == "on"
    settings.update({"wandb": track})
    if track:
        wandb.init(project=a.wandb_project, name=name, job_type="train", config=vars(a))
    else:
        print("W&B: off (set RS_EXPERIMENT_TRACKING=on to log this run)")
    YOLO(a.model).train(
        data=resolve_data(a.data), epochs=a.epochs, imgsz=a.imgsz, batch=a.batch, device=device,
        workers=a.workers, amp=device == 0, patience=a.patience, freeze=a.freeze, name=name,
        project=str(HERE / "runs" / "detect"),
        # Brightness/saturation jitter approximates night and bad-weather footage.
        hsv_v=0.5, hsv_s=0.6, fliplr=0.5, close_mosaic=10,
    )


if __name__ == "__main__":
    main()
