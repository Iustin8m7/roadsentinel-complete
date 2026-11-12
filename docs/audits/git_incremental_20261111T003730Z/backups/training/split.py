"""Split labeled frames into training/datasets/roadsentinel/{images,labels}/{train,val,test}.

With few source videos a per-video split leaves whole scenes out of training, and a random frame
split leaks near-identical neighbouring frames into val. So each video is split in time instead:
the last --val fraction of its frames (one contiguous block) goes to val, the rest to train.
Frames from --test-frames (a separately extracted, held-out segment) are copied to test unchanged.
--val-frames does the same for val (e.g. a later recording), usually with --val 0 so every frame
under --frames goes to train.

After splitting, describe the sets with training/make_manifest.py and run training/check_dataset.py
(leakage by bytes and by time gap, label sanity, data card). See docs/LABELING_GUIDE.md.

Usage: python training/split.py [--val 0.2] [--val-frames DIR] [--test-frames training/frames-test]
"""
import argparse
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def labeled(frames: Path) -> list[Path]:
    return sorted(p for p in frames.rglob("*.jpg") if p.with_suffix(".txt").exists())


def copy(img: Path, out: Path, split: str) -> None:
    for kind, src in (("images", img), ("labels", img.with_suffix(".txt"))):
        dst = out / kind / split / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default=str(ROOT / "training" / "frames"))
    ap.add_argument("--val-frames", help="held-out labeled frames to copy into the val split")
    ap.add_argument("--test-frames", help="held-out labeled frames to copy into the test split")
    ap.add_argument("--out", default=str(ROOT / "training" / "datasets" / "roadsentinel"))
    ap.add_argument("--val", type=float, default=0.2, help="tail fraction of each video used for val")
    a = ap.parse_args()

    by_video = defaultdict(list)
    for img in labeled(Path(a.frames)):
        by_video[img.stem.rsplit("_", 1)[0]].append(img)
    if not by_video:
        raise SystemExit("No labeled frames (jpg + txt). Run prelabel.py and review the labels first.")

    out = Path(a.out)
    shutil.rmtree(out, ignore_errors=True)
    counts = defaultdict(int)
    for video, imgs in sorted(by_video.items()):
        imgs.sort(key=lambda p: int(p.stem.rsplit("_", 1)[1]))
        cut = len(imgs) - (max(1, round(len(imgs) * a.val)) if a.val > 0 else 0)
        for j, img in enumerate(imgs):
            s = "train" if j < cut else "val"
            copy(img, out, s)
            counts[s] += 1
        print(f"{video}: train {cut}, val {len(imgs) - cut}")
    for split, frames in (("val", a.val_frames), ("test", a.test_frames)):
        if not frames:
            continue
        held = labeled(Path(frames))
        if not held:
            raise SystemExit(f"No labeled frames under {frames}.")
        for img in held:
            copy(img, out, split)
        counts[split] += len(held)
    print(f"train: {counts['train']}, val: {counts['val']}, test: {counts['test']} frames -> {out}")


if __name__ == "__main__":
    main()
