#!/usr/bin/env python3
"""Register new detector weights as a `candidate` (validates they load, match the class map and are new).

    python scripts/model_install.py path/to/best.pt --id rs-yolo11s-iasi-v2 \
        --base yolo11s.pt --data "633 train / 281 val frames, Iasi cameras 2026-10-20" \
        --trained-on 2026-11-02 [--cameras iasi-piata-unirii ...] [--notes "..."]

Never overwrites an active model or existing weights. Metrics stay empty until training/eval.py runs.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from roadsentinel import models


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("weights")
    ap.add_argument("--id", required=True, dest="model_id")
    ap.add_argument("--base", required=True, help="base model the fine-tune started from")
    ap.add_argument("--data", required=True, help="description of the training data (sources, sizes, licence/consent)")
    ap.add_argument("--trained-on", required=True, help="training date YYYY-MM-DD")
    ap.add_argument("--cameras", nargs="*", default=["*"], help="camera ids this model is meant for (default: any)")
    ap.add_argument("--notes", default="")
    a = ap.parse_args(argv)
    try:
        e = models.install(a.weights, a.model_id, base_model=a.base, training_data=a.data, trained_on=a.trained_on,
                           cameras=a.cameras, notes=a.notes)
    except models.ModelError as err:
        print(f"REFUSED: {err}", file=sys.stderr)
        return 2
    print(f"registered {e['id']} (candidate) sha256 {e['sha256'][:16]}...  file {e['file']}")
    print("next: python training/eval.py --model", e["id"], "--test models/manifests/test.json --train models/manifests/train.json --val models/manifests/val.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
