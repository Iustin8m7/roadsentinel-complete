#!/usr/bin/env python3
"""Guarded additive 0025 upgrade for one explicitly identified local integration DB.

Backs up the DB and evidence, restores the dump to a fresh disposable database,
rehearses Alembic there, and only then upgrades the named live target with --apply.
No database is dropped or reseeded. The restored copy and backup are retained.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql
from sqlalchemy.engine import make_url


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def run(args: list[str], log: Path, *, env: dict[str, str] | None = None) -> None:
    with log.open("a") as out:
        result = subprocess.run(args, stdout=out, stderr=out, env=env, check=False, timeout=240)
    if result.returncode:
        raise RuntimeError(f"Command failed ({Path(args[0]).name}); see private log")


def identity(conn) -> tuple[str, str, int, str, str]:
    row = conn.execute(
        "SELECT current_database(), host(inet_server_addr()), inet_server_port(), current_user, system_identifier::text FROM pg_control_system()"
    ).fetchone()
    return tuple(row)


def digest_tree(source: Path, target: Path) -> dict[str, str]:
    result = {}
    for item in source.rglob("*"):
        if item.is_symlink():
            raise RuntimeError("Evidence tree contains a symlink; manual preservation required")
        if not item.is_file():
            continue
        relative = item.relative_to(source)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, destination)
        digest = hashlib.sha256(item.read_bytes()).hexdigest()
        if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise RuntimeError("Evidence backup checksum mismatch")
        result[str(relative)] = digest
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--admin-user", required=True)
    parser.add_argument("--expect-system-id", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    env_file = args.env_file.resolve()
    if not env_file.is_relative_to(ROOT) or not env_file.is_file():
        raise RuntimeError("Environment file must be in the integration workspace")
    values = {k: v for k, v in dotenv_values(env_file).items() if v is not None}
    app = make_url(values["RS_DATABASE_URL"])
    if app.host not in ("127.0.0.1", "localhost") or not app.port or not app.database:
        raise RuntimeError("Only an explicitly configured local database is supported")
    admin_url = f"postgresql://{args.admin_user}@{app.host}:{app.port}/{app.database}"
    expected = (app.database, "127.0.0.1", app.port, args.admin_user, args.expect_system_id)
    with psycopg.connect(admin_url, connect_timeout=3) as db:
        if identity(db) != expected:
            raise RuntimeError("Database identity/system identifier mismatch; refusing backup or upgrade")
        current = db.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        if current not in ("0024", "0025", "0026", "0027"):
            raise RuntimeError(f"Expected revision 0024 through 0027; found {current}")
        before = {
            table: db.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]
            for table in ("tenants", "users", "alerts", "evidence", "recordings", "location_revisions")
        }
    evidence = Path(values["RS_EVIDENCE_DIR"]).resolve()
    if not evidence.is_dir():
        raise RuntimeError("Configured evidence directory does not exist")
    os.umask(0o077)
    backup_dir = BACKEND / ".integration-backups" / ("notifications-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    backup_dir.mkdir(parents=True, mode=0o700)
    dump = backup_dir / "database.dump"
    log = backup_dir / "upgrade.log"
    manifest = {"identity": expected, "before_counts": before, "created_at": datetime.now(UTC).isoformat()}
    run([str(args.pg_bin / "pg_dump"), "--format=custom", "--file", str(dump), "--dbname", admin_url], log)
    run([str(args.pg_bin / "pg_restore"), "--list", str(dump)], log)
    manifest["dump_sha256"] = hashlib.sha256(dump.read_bytes()).hexdigest()
    manifest["evidence_sha256"] = digest_tree(evidence, backup_dir / "evidence")
    clone_name = "rsmission_rehearsal_" + uuid.uuid4().hex[:10]
    root_url = f"postgresql://{args.admin_user}@{app.host}:{app.port}/postgres"
    with psycopg.connect(root_url, autocommit=True, connect_timeout=3) as root:
        if identity(root)[2:] != expected[2:]:
            raise RuntimeError("Server identity changed during backup")
        root.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(clone_name)))
    clone_url = f"postgresql://{args.admin_user}@{app.host}:{app.port}/{clone_name}"
    manifest["rehearsal_database"] = clone_name
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    run([str(args.pg_bin / "pg_restore"), "--exit-on-error", "--no-owner", "--dbname", clone_url, str(dump)], log)
    with psycopg.connect(clone_url) as clone:
        if identity(clone)[0] != clone_name:
            raise RuntimeError("Restore database identity mismatch")
        for table, count in before.items():
            actual = clone.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]
            if actual != count:
                raise RuntimeError(f"Restored count mismatch for {table}")
    migrate_env = {**os.environ, **values, "PYTHONPATH": str(BACKEND),
                   "RS_DATABASE_URL": app.set(database=clone_name).render_as_string(hide_password=False),
                   "RS_MIGRATOR_DATABASE_URL": clone_url.replace("postgresql://", "postgresql+psycopg://")}
    run([sys.executable, "-m", "alembic", "-c", str(BACKEND / "alembic.ini"), "upgrade", "head"], log, env=migrate_env)
    with psycopg.connect(clone_url) as clone:
        if clone.execute("SELECT version_num FROM alembic_version").fetchone()[0] != "0028":
            raise RuntimeError("Rehearsal revision mismatch")
        policies = clone.execute("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid IN ('notification_events'::regclass,'notification_receipts'::regclass)").fetchall()
        if len(policies) != 2 or not all(a and b for a, b in policies):
            raise RuntimeError("Rehearsal RLS mismatch")
    manifest["rehearsal_verified"] = True
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    if not args.apply:
        print(f"Backup and isolated restore verified: {backup_dir}; live DB unchanged")
        return
    with psycopg.connect(admin_url, connect_timeout=3) as live:
        if identity(live) != expected or live.execute("SELECT version_num FROM alembic_version").fetchone()[0] != current:
            raise RuntimeError("Live identity or revision changed before upgrade")
    live_env = {**os.environ, **values, "PYTHONPATH": str(BACKEND),
                "RS_MIGRATOR_DATABASE_URL": admin_url.replace("postgresql://", "postgresql+psycopg://")}
    run([sys.executable, "-m", "alembic", "-c", str(BACKEND / "alembic.ini"), "upgrade", "head"], log, env=live_env)
    with psycopg.connect(admin_url) as live:
        if identity(live) != expected or live.execute("SELECT version_num FROM alembic_version").fetchone()[0] != "0028":
            raise RuntimeError("Live upgrade verification failed")
        for table, count in before.items():
            actual = live.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]
            if actual < count:
                raise RuntimeError(f"Pre-existing {table} row count fell")
    manifest["live_upgraded"] = True
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    print(f"Revision 0028 applied after backup and isolated restore: {backup_dir}")


if __name__ == "__main__":
    main()
