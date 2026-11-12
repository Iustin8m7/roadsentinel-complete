#!/usr/bin/env python3
"""Demonstrate that the audit hash chain detects tampering by a privileged insider.

1. Verifies the tenant's chain (expect OK).
2. Connects as the PostgreSQL *superuser*, disables triggers for that session
   (session_replication_role = replica) and silently edits one audit entry.
3. Verifies again: the chain reports the first broken entry.
4. Restores the original value (unless --keep) so the demo can be repeated.

Needs RS_ADMIN_DATABASE_URL (superuser) and RS_DATABASE_URL in the environment.
Docker:  docker compose -f deploy/docker-compose.yml run --rm migrate \
             python scripts/audit_tamper_demo.py --tenant unit-a
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for candidate in (ROOT / "backend", ROOT):
    if (candidate / "app").is_dir():
        sys.path.insert(0, str(candidate))
        break

import psycopg
from app.core.audit import verify_chain
from app.db import tenant_session
from app.services.seed import tenant_id_for_slug
from sqlalchemy.engine import make_url


def verify(tenant_id: object, label: str) -> bool:
    with tenant_session(tenant_id) as db:  # type: ignore[arg-type]
        result = verify_chain(db, tenant_id)  # type: ignore[arg-type]
    status = "OK" if result.ok else f"BROKEN at seq {result.first_broken_seq} ({result.reason})"
    print(f"[{label}] checked {result.checked} entries -> {status}")
    return result.ok


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", default="unit-a")
    parser.add_argument("--seq", type=int, default=None, help="entry to tamper (default: middle)")
    parser.add_argument("--keep", action="store_true", help="do not restore the original value")
    args = parser.parse_args()

    admin = os.environ.get("RS_ADMIN_DATABASE_URL")
    if not admin:
        sys.exit("RS_ADMIN_DATABASE_URL is required (superuser connection)")
    db_name = make_url(os.environ["RS_DATABASE_URL"]).database
    admin_dsn = (
        make_url(admin)
        .set(database=db_name)
        .render_as_string(hide_password=False)
        .replace("postgresql+psycopg://", "postgresql://", 1)
    )
    tenant_id = tenant_id_for_slug(args.tenant)
    if tenant_id is None:
        sys.exit(f"unknown tenant {args.tenant!r} (did you run the seed?)")

    if not verify(tenant_id, "before"):
        sys.exit("chain already broken; aborting")

    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        count = conn.execute(
            "SELECT count(*) FROM audit_log WHERE tenant_id = %s", (tenant_id,)
        ).fetchone()[0]  # type: ignore[index]
        seq = args.seq or max(1, count // 2)
        original = conn.execute(
            "SELECT action, details::text FROM audit_log WHERE tenant_id = %s AND seq = %s",
            (tenant_id, seq),
        ).fetchone()
        if original is None:
            sys.exit(f"no entry with seq {seq}")
        print(f"\nInsider (superuser, triggers disabled) rewrites entry #{seq}: "
              f"action {original[0]!r} -> 'audit.verified', details -> {{}}")
        conn.execute("SET session_replication_role = replica")
        conn.execute(
            "UPDATE audit_log SET action = 'audit.verified', details = '{}'::jsonb "
            "WHERE tenant_id = %s AND seq = %s",
            (tenant_id, seq),
        )
        print("Also note: as the app role this UPDATE is impossible (no privilege + trigger).\n")
        detected = not verify(tenant_id, "after tamper")
        if not args.keep:
            conn.execute(
                "UPDATE audit_log SET action = %s, details = %s::jsonb WHERE tenant_id = %s AND seq = %s",
                (original[0], original[1], tenant_id, seq),
            )
            print("\nOriginal value restored.")
            verify(tenant_id, "after restore")
    sys.exit(0 if detected else 1)


if __name__ == "__main__":
    main()
