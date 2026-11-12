"""Build a train / val / test manifest from a folder of labelled frames.

    python training/make_manifest.py --images data/iasi-test --camera iasi-piata-unirii --tags night \
        --out models/manifests/test.json [--time-regex '(\\d{8}_\\d{6})'] [--time-format %Y%m%d_%H%M%S]

Each image needs a YOLO label file with the same stem (.txt). The capture time comes from the file
name (regex) or, failing that, the file's modification time: say so in the data card if you rely on
mtime. Manifests are what training/eval.py uses to prove the test set shares nothing with training.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def build(images, camera, tags, time_regex, time_format, base):
    items = []
    rx = re.compile(time_regex)
    for img in sorted(Path(images).resolve().rglob("*")):
        if img.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        label = img.with_suffix(".txt")
        m = rx.search(img.stem)
        when = datetime.strptime(m.group(1), time_format) if m else datetime.fromtimestamp(img.stat().st_mtime)
        items.append({"image": os.path.relpath(img, base), "labels": os.path.relpath(label, base) if label.exists() else None,
                      "camera": camera, "captured_at": when.isoformat(timespec="seconds"), "tags": tags,
                      "time_source": "filename" if m else "mtime"})
    return items


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", required=True)
    ap.add_argument("--camera", required=True)
    ap.add_argument("--tags", nargs="*", default=[])
    ap.add_argument("--time-regex", default=r"(\d{8}_\d{6})")
    ap.add_argument("--time-format", default="%Y%m%d_%H%M%S")
    ap.add_argument("--name")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    items = build(a.images, a.camera, a.tags, a.time_regex, a.time_format, out.parent)
    unlabeled = [i["image"] for i in items if not i["labels"]]
    if not items:
        print("no images found", file=sys.stderr)
        return 2
    out.write_text(json.dumps({"name": a.name or out.stem, "items": items}, indent=1))
    print(f"{out}: {len(items)} items, {len(unlabeled)} without labels, time from mtime for "
          f"{sum(i['time_source'] == 'mtime' for i in items)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
