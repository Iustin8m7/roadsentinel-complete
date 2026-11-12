#!/usr/bin/env python3
"""Docs sanity check: every relative Markdown link must point to an existing file, and docs must
be checked without requiring Git metadata. Run from anywhere: python scripts/check_docs.py"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SKIP_DIRS = {"node_modules", ".venv", ".venv.integration", "dist"}
# Frozen evidence quotes retain the original document's link base.
FROZEN_EVIDENCE = {"docs/audits/runtime_verification/README_AUDIT_AFTER_BEFORE_LOGIN_RECOVERY.md"}
FROZEN_BASES = {
    # This verbatim historical report retains links relative to its original audit folder.
    "docs/audits/runtime_verification/ISSUES_AND_UNVERIFIED_EVIDENCE_BEFORE_BROWSER_20261111.md":
        ROOT / "docs/audits",
}


def md_files() -> list[Path]:
    files = []
    for directory, dirs, names in os.walk(ROOT):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS | {".git", "data", "dist-real", "dist-mock"}]
        files.extend(Path(directory) / name for name in names if name.endswith(".md"))
    return sorted(files)


def main() -> int:
    bad = []
    for f in md_files():
        if f.relative_to(ROOT).as_posix() in FROZEN_EVIDENCE:
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        in_code = False
        for n, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_code = not in_code
            if in_code:
                continue
            for target in LINK.findall(line):
                if re.match(r"^(https?:|mailto:|#)", target):
                    continue
                path = target.split("#", 1)[0]
                base = FROZEN_BASES.get(f.relative_to(ROOT).as_posix(), f.parent)
                if path and not (base / path).resolve().exists():
                    bad.append(f"{f.relative_to(ROOT)}:{n}: broken link -> {target}")
    for b in bad:
        print(b)
    print(f"{len(bad)} broken link(s) in {len(md_files())} markdown files")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
