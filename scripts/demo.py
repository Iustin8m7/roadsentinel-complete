#!/usr/bin/env python3
"""One-command LOCAL demo (Linux, macOS, Windows): API + seeded SYNTHETIC data. No Docker needed
if you already have a PostgreSQL superuser URL.

    python scripts/demo.py                       # strict profile: MFA mandatory (scan the QR code)
    python scripts/demo.py --profile demo        # two password-only accounts for a stage demo (local only)
    python scripts/demo.py --admin-url postgresql://postgres:secret@localhost:5432/postgres

Profiles
  strict  production-like: no MFA exemption anywhere. Accounts enroll TOTP on first login.
  demo    RS_MFA_EXEMPTION_ENABLED=true for admin@/operator@roadsentinel.local ONLY, ONLY in this
          local RS_ENV=dev process. The exemption is refused by the API in production.
Everything is generated fresh: secrets go to .env.demo (git-ignored), passwords are printed once.
All alerts/evidence are produced by app.services.seed and carry details.synthetic=true (shown as SINTETIC).
Open the UI with:  cd frontend && npm ci && npm run dev   (proxies /api to http://localhost:8000)
"""
import argparse
import base64
import os
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"


def b64(n):
    return base64.b64encode(secrets.token_bytes(n)).decode()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", choices=["strict", "demo"], default="strict")
    ap.add_argument("--admin-url", default=os.environ.get("RS_DEMO_ADMIN_URL", "postgresql://postgres:postgres@localhost:5432/postgres"))
    ap.add_argument("--db", default="roadsentinel_demo")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-serve", action="store_true", help="prepare the database, print the command, do not start the API")
    a = ap.parse_args(argv)

    from urllib.parse import urlsplit

    admin = urlsplit(a.admin_url)
    host = f"{admin.hostname}:{admin.port or 5432}"
    owner_pw, app_pw, seed_pw = secrets.token_urlsafe(18), secrets.token_urlsafe(18), secrets.token_urlsafe(18)

    def url(user, pw, db):
        return f"postgresql+psycopg://{user}:{pw}@{host}/{db}"

    env = {
        **os.environ,
        "RS_ENV": "dev", "RS_COOKIE_SECURE": "false", "RS_PUBLIC_ORIGIN": "http://localhost:5173",
        "RS_JWT_SECRET": secrets.token_urlsafe(48), "RS_URL_SIGNING_KEY": secrets.token_urlsafe(48),
        "RS_MASTER_KEYS": "1:" + b64(32), "RS_MASTER_KEY_CURRENT": "1",
        "RS_ADMIN_DATABASE_URL": a.admin_url.replace("postgresql://", "postgresql+psycopg://", 1),
        "RS_MIGRATOR_DATABASE_URL": url("rs_owner", owner_pw, a.db),
        "RS_DATABASE_URL": url("rs_app", app_pw, a.db),
        "RS_SEED_PASSWORD": seed_pw,
        "RS_EVIDENCE_DIR": str(ROOT / "data" / "demo-evidence"),
        "RS_MFA_EXEMPTION_ENABLED": "true" if a.profile == "demo" else "false",
    }
    # keep the secrets next to the repo (git-ignored: .env.*) so the API can be restarted
    keys = [k for k in env if k.startswith("RS_")]
    (ROOT / ".env.demo").write_text("\n".join(f"{k}={env[k]}" for k in keys) + "\n")

    def cli(*args):
        subprocess.run([sys.executable, "-m", "app.cli", *args], cwd=BACKEND, env=env, check=True)

    cli("bootstrap-db")
    cli("migrate")
    cli("seed")
    pw = secrets.token_urlsafe(18)
    cli("demo-accounts", "--tenant", "unit-a", "--password", pw, *(["--exempt-mfa"] if a.profile == "demo" else []))
    print("\n=== DEMO READY (synthetic data) ===")
    print(f"profile: {a.profile}  |  accounts: admin@roadsentinel.local, operator@roadsentinel.local")
    print(f"one-time password for both (not stored anywhere else): {pw}")
    print("MFA:", "password only (local demo exemption)" if a.profile == "demo" else "mandatory: enroll TOTP on first login")
    print("Seeded accounts of the other roles use RS_SEED_PASSWORD from .env.demo (they require MFA enrollment).")
    cmd = [sys.executable, "-m", "uvicorn", "app.main:create_app", "--factory", "--port", str(a.port)]
    print("API:", " ".join(cmd), "(from backend/, with the variables in .env.demo)")
    if a.no_serve:
        return 0
    subprocess.run(cmd, cwd=BACKEND, env=env, check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
