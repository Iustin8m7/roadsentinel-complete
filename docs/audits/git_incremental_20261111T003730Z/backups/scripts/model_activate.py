#!/usr/bin/env python3
"""Make a registered model the active one for ONE camera (edits cameras/<id>.yaml: model + model_id).

    python scripts/model_activate.py rs-yolo11s-iasi-v2 cameras/iasi-piata-unirii.yaml \
        [--smoke-frames a.jpg b.jpg] [--expect car] [--allow-unevaluated]

Checks: registered, applicable to the camera, sha256 matches, evaluated (unless overridden), smoke test.
Writes a hash-chained record to models/changes.jsonl. The previous model is kept: model_rollback.py.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from roadsentinel import models


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model_id")
    ap.add_argument("camera_yaml")
    ap.add_argument("--smoke-frames", nargs="*", default=[str(models.ROOT / "tests" / "fixtures" / "redaction-demo.jpg")])
    ap.add_argument("--expect", nargs="*", default=[], help="class names the smoke frames must contain")
    ap.add_argument("--no-smoke", action="store_true")
    ap.add_argument("--allow-unevaluated", action="store_true", help="activate without an eval report (recorded as such)")
    a = ap.parse_args(argv)
    try:
        r = models.activate(a.model_id, a.camera_yaml, frames=[] if a.no_smoke else a.smoke_frames,
                            expect_classes=a.expect, require_eval=not a.allow_unevaluated)
    except models.ModelError as err:
        print(f"REFUSED: {err}", file=sys.stderr)
        return 2
    print(f"{r['camera']}: now {r['model']} (was {r['previous']}). Roll back with scripts/model_rollback.py {a.camera_yaml}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
