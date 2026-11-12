#!/usr/bin/env python3
"""Print a current TOTP for an explicitly selected local development authenticator.

This uses the real enrolled second factor; it does not skip MFA. Prefer importing
its private QR into your own phone. Never use these development helpers in production.
"""

import argparse
import json
import stat
from pathlib import Path

import pyotp

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("email")
args = p.parse_args()
file = ROOT / "backend/.integration-authenticators/authenticators.json"
if stat.S_IMODE(file.stat().st_mode) != 0o600:
    raise SystemExit("Refusing authenticator file without mode 0600")
entry = json.loads(file.read_text()).get(args.email)
if not entry:
    raise SystemExit("No verified local development authenticator for this account")
print(pyotp.TOTP(entry["secret"]).now())
