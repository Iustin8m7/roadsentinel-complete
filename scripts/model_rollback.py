#!/usr/bin/env python3
"""Instantly return a camera to the model it used before its last activation (weights are never deleted).

    python scripts/model_rollback.py cameras/iasi-piata-unirii.yaml
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from roadsentinel import models


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    try:
        r = models.rollback(argv[0])
    except models.ModelError as err:
        print(f"REFUSED: {err}", file=sys.stderr)
        return 2
    print(f"{r['camera']}: rolled back to {r['model']} (was {r['previous']}). Restart that camera's pipeline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
