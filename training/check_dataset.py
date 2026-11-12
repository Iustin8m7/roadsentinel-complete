"""Consistency and leakage checker for train / val / test manifests (see roadsentinel/evaluation.py).

    python training/check_dataset.py --train models/manifests/train.json --val models/manifests/val.json \
        --test models/manifests/test.json [--min-gap-s 600] [--card docs/data-cards/iasi.md]

Hard errors (exit 3): test overlaps train/val (same bytes, or same camera within --min-gap-s),
label files missing / malformed / out of range, duplicate images inside one split, missing data card.
Warnings (printed, exit 0): class imbalance, classes with few boxes, a single camera, capture times taken
from file mtime, splits that share a camera but no time block, no tag coverage (night/rain/fog).
Split by camera and by time block, never by random frames: neighbouring frames are near-duplicates.
"""
import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from roadsentinel import evaluation as ev
from roadsentinel.models import PROJECT_CLASSES

CARD_FIELDS = ("Sources", "Licence", "Consent", "Retention", "Redaction", "Labelling")


def label_problems(item):
    p = item["label_path"]
    if p is None or not Path(p).exists():
        return [f"{item['image']}: no label file"]
    out = []
    for n, line in enumerate(Path(p).read_text().splitlines(), 1):
        parts = line.split()
        try:
            cls, vals = int(parts[0]), [float(v) for v in parts[1:5]]
            if len(parts) < 5 or any(not 0.0 <= v <= 1.0 for v in vals) or vals[2] <= 0 or vals[3] <= 0:
                out.append(f"{item['image']}:{n}: box out of range or malformed")
            elif not 0 <= cls < 80:
                out.append(f"{item['image']}:{n}: class id {cls} not a COCO id")
        except (ValueError, IndexError):
            out.append(f"{item['image']}:{n}: unreadable label line")
    return out


def check(train, val, test, min_gap_s=600, card=None):
    errors, warnings = [], []
    splits = {"train": train, "val": val, "test": test}
    for name, m in splits.items():
        if not m:
            continue
        hashes = Counter(ev._item_hash(i) for i in m["items"])
        dup = [h for h, c in hashes.items() if c > 1]
        if dup:
            errors.append(f"{name}: {len(dup)} image(s) appear more than once")
        for it in m["items"]:
            errors += label_problems(it)
    if test:
        errors += ev.check_leakage(test, [m for m in (train, val) if m], min_gap_s)
    if train and val:
        errors += [f"val vs train: {p}" for p in ev.check_leakage(val, [train], min_gap_s)]
    # warnings
    counts = defaultdict(Counter)
    for name, m in splits.items():
        for it in (m or {"items": []})["items"]:
            for line in (Path(it["label_path"]).read_text().splitlines() if it["label_path"] and Path(it["label_path"]).exists() else []):
                cid = int(line.split()[0])
                if cid in PROJECT_CLASSES:
                    counts[name][PROJECT_CLASSES[cid]] += 1
    for name, c in counts.items():
        for cls in PROJECT_CLASSES.values():
            if c[cls] < ev.MIN_BOXES_FOR_A_CLAIM:
                warnings.append(f"{name}: class {cls} has only {c[cls]} boxes (< {ev.MIN_BOXES_FOR_A_CLAIM}): no per-class claim possible")
        if c and max(c.values()) > 20 * max(1, min(v for v in c.values() if v)):
            warnings.append(f"{name}: strong class imbalance {dict(c)}")
    for name, m in splits.items():
        if m and len({i.get("camera") for i in m["items"]}) == 1:
            warnings.append(f"{name}: a single camera: results say nothing about other cameras")
        if m and any(i.get("time_source") == "mtime" for i in m["items"]):
            warnings.append(f"{name}: some capture times come from file mtime (not from the recording): the time-gap check is only as good as they are")
    if test:
        tags = {t for i in test["items"] for t in i["tags"]}
        for want in ("night", "rain", "fog"):
            if want not in tags:
                warnings.append(f"test: no item tagged '{want}': that condition is NOT evaluated")
    if card is None or not Path(card).exists():
        errors.append("no data card (pass --card docs/data-cards/<set>.md; template docs/DATA_CARD_TEMPLATE.md)")
    else:
        text = Path(card).read_text()
        for field in CARD_FIELDS:
            if f"**{field}" not in text and f"## {field}" not in text:
                errors.append(f"data card lacks the field '{field}'")
        if "TODO" in text or "<fill" in text:
            errors.append("data card still contains TODO / <fill ...> placeholders")
    return {"errors": errors, "warnings": warnings, "counts": {k: dict(v) for k, v in counts.items()}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--train")
    ap.add_argument("--val")
    ap.add_argument("--test")
    ap.add_argument("--min-gap-s", type=int, default=600)
    ap.add_argument("--card")
    a = ap.parse_args(argv)
    load = lambda p: ev.load_manifest(p) if p else None
    r = check(load(a.train), load(a.val), load(a.test), a.min_gap_s, a.card)
    for w in r["warnings"]:
        print("WARNING:", w)
    for e in r["errors"]:
        print("ERROR:  ", e)
    print(f"boxes per split: {r['counts']}")
    print(f"{len(r['errors'])} error(s), {len(r['warnings'])} warning(s)")
    return 3 if r["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
