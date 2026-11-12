#!/usr/bin/env python3
"""Seed development data (2 police units + platform admin). Thin wrapper around
``python -m app.cli seed`` so it can be run from the repository root or inside the backend
container:

    docker compose --env-file .env -f deploy/docker-compose.yml exec backend python scripts/seed.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for candidate in (ROOT / "backend", ROOT):
    if (candidate / "app").is_dir():
        sys.path.insert(0, str(candidate))
        break

from app.cli import main

if __name__ == "__main__":
    main(["seed"])
