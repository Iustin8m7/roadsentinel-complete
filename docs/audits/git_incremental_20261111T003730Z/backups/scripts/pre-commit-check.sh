#!/usr/bin/env bash
# Optional pre-commit hook:  ln -s ../../scripts/pre-commit-check.sh .git/hooks/pre-commit
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
python3 scripts/scan_secrets.py
