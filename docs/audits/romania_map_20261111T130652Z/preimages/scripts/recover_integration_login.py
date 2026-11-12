#!/usr/bin/env python3
"""Guarded integration-only login recovery; default is read-only inspection.

Apply creates a private backup, restores/rehearses on a brand-new isolated PostgreSQL
cluster, verifies every public-table row digest, then hardens only identifier lookup
ownership and applies the rehearsed additive migration. Never resets an existing DB.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
from app.services.lookup_roles import install_lookup_owner

EXPECTED = ("rsint_20261110b", "127.0.0.1", 55446, "rsint_root_261110")
SYSTEM_ID = "7706309627307635180"
PG = Path("/home/justin7m8/miniconda3/envs/rs-pg/bin")


def config():
    from dotenv import dotenv_values

    values = {k: v for k, v in dotenv_values(BACKEND / ".env.integration.local").items() if v is not None}
    app = make_url(values["RS_DATABASE_URL"])
    if (app.database, app.host, app.port, app.username) != (EXPECTED[0], EXPECTED[1], EXPECTED[2], "rsint_app_261110b"):
        raise RuntimeError("Integration application URL identity mismatch")
    creds = json.loads((BACKEND / ".integration-test-credentials.json").read_text())
    if creds["database"] != EXPECTED[0]:
        raise RuntimeError("Credential file database mismatch")
    return values, app, creds


def identity(conn):
    value = conn.execute(
        "SELECT current_database(),host(inet_server_addr()),inet_server_port(),current_user"
    ).fetchone()
    if (
        value != EXPECTED
        or conn.execute("SELECT system_identifier::text FROM pg_control_system()").fetchone()[0] != SYSTEM_ID
    ):
        raise RuntimeError("Refusing unexpected integration database, server system identifier or admin role")
    return value


def fingerprints(conn):
    conn.execute("SET TIME ZONE 'UTC'")
    result = {}
    tables = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
    for (name,) in tables:
        digest = hashlib.sha256()
        count = 0
        for (row,) in conn.execute(
            sql.SQL("SELECT row_to_json(t)::text FROM public.{} t ORDER BY row_to_json(t)::text").format(
                sql.Identifier(name)
            )
        ):
            digest.update(row.encode())
            digest.update(b"\n")
            count += 1
        result[name] = {"rows": count, "sha256": digest.hexdigest()}
    return result


def run(command, *, env=None, log):
    completed = subprocess.run(command, env=env, stdout=log, stderr=log, timeout=180, check=False)
    if completed.returncode:
        raise RuntimeError("Recovery subcommand failed; inspect the private recovery log")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument(
        "--rehearse-only", action="store_true", help="Backup and verify isolated restore without changing the live DB"
    )
    args = ap.parse_args()
    if ROOT.resolve() != Path("/home/justin7m8/Documents/roadsentinel-integration"):
        raise RuntimeError("Recovery script may run only in the approved integration workspace")
    values, app, _creds = config()
    admin_url = f"postgresql://{EXPECTED[3]}@127.0.0.1:55446/{EXPECTED[0]}"
    with psycopg.connect(admin_url, connect_timeout=3) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        print("Verified integration identity:", identity(conn), "system identifier:", SYSTEM_ID)
        owner = conn.execute(
            "SELECT proowner::regrole::text FROM pg_proc WHERE oid='rs_tenant_id_by_slug(text)'::regprocedure"
        ).fetchone()[0]
        if owner not in ("rsint_owner_261110b", "rsint_app_261110b__lookup"):
            raise RuntimeError("Unexpected current lookup function owner")
        print(
            "Current lookup owner:",
            owner,
            "tenant/user counts:",
            conn.execute("SELECT (SELECT count(*) FROM tenants),(SELECT count(*) FROM users)").fetchone(),
        )
        before = fingerprints(conn)
        original_functions = conn.execute(
            "SELECT p.oid::regprocedure::text,proowner::regrole::text FROM pg_proc p WHERE proname IN ('rs_tenant_id_by_slug','rs_platform_tenant','rs_auth_find_user','rs_auth_find_refresh_tenant','rs_auth_find_invitation_tenant','rs_resource_tenant') AND pronamespace='public'::regnamespace"
        ).fetchall()
    if not (args.apply or args.rehearse_only):
        print("INSPECTION ONLY. --apply first creates and verifies a backup by isolated restore.")
        return
    os.umask(0o077)
    folder = BACKEND / ".integration-backups" / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    folder.mkdir(parents=True, mode=0o700)
    backup = folder / "integration.dump"
    with (folder / "recovery.log").open("w") as log:
        run([str(PG / "pg_dump"), "--format=custom", "--file", str(backup), "--dbname", admin_url], log=log)
        run([str(PG / "pg_restore"), "--list", str(backup)], log=log)
        backup.chmod(0o600)
        metadata = {
            "identity": EXPECTED,
            "system_identifier": SYSTEM_ID,
            "backup_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
            "before": before,
            "time": datetime.now(UTC).isoformat(),
            "function_owners": original_functions,
        }
        (folder / "metadata.json").write_text(json.dumps(metadata, indent=2))
        with (folder / "rollback-lookup-owners.sql").open("w") as rollback:
            rollback.write(
                "-- Guard identity with metadata.json first. Restores previous ownership only; may restore the old login failure.\nBEGIN;\n"
            )
            for signature, previous in original_functions:
                rollback.write(
                    sql.SQL("ALTER FUNCTION public." + signature + " OWNER TO {};\n")
                    .format(sql.Identifier(previous))
                    .as_string()
                )
            rollback.write("COMMIT;\n")
        with tempfile.TemporaryDirectory(prefix="rslogin-rehearsal-") as temp:
            temp = Path(temp)
            data = temp / "pg"
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            run(
                [
                    str(PG / "initdb"),
                    "-D",
                    str(data),
                    "-U",
                    EXPECTED[3],
                    "-A",
                    "trust",
                    "--encoding=UTF8",
                    "--no-locale",
                ],
                log=log,
            )
            run(
                [
                    str(PG / "pg_ctl"),
                    "-D",
                    str(data),
                    "-l",
                    str(temp / "pg.log"),
                    "-o",
                    f"-h 127.0.0.1 -p {port} -k {temp}",
                    "start",
                ],
                log=log,
            )
            try:
                clone_db = "rslogin_restore_" + uuid.uuid4().hex[:12]
                clone_url = f"postgresql://{EXPECTED[3]}@127.0.0.1:{port}/{clone_db}"
                with psycopg.connect(
                    host="127.0.0.1", port=port, dbname="postgres", user=EXPECTED[3], autocommit=True
                ) as clone:
                    assert clone.execute("SELECT inet_server_port()").fetchone()[0] == port
                    clone.execute(sql.SQL("CREATE ROLE {} LOGIN NOBYPASSRLS").format(sql.Identifier(app.username)))
                    clone.execute("CREATE ROLE rsint_owner_261110b LOGIN NOBYPASSRLS")
                    clone.execute(
                        sql.SQL("CREATE ROLE {} NOLOGIN NOSUPERUSER NOINHERIT BYPASSRLS").format(
                            sql.Identifier(app.username + "__lookup")
                        )
                    )
                    clone.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(clone_db)))
                run(
                    [str(PG / "pg_restore"), "--exit-on-error", "--no-owner", "--dbname", clone_url, str(backup)],
                    log=log,
                )
                with psycopg.connect(clone_url) as clone:
                    restored = fingerprints(clone)
                    if restored != before:
                        raise RuntimeError("Restored backup row digests differ")
                    install_lookup_owner(clone, app.username)
                clone_env = {
                    **os.environ,
                    **values,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONPATH": os.pathsep.join((str(BACKEND), str(ROOT))),
                    "RS_DATABASE_URL": app.set(port=port, database=clone_db).render_as_string(hide_password=False),
                    "RS_MIGRATOR_DATABASE_URL": clone_url.replace("postgresql://", "postgresql+psycopg://"),
                    "RS_ADMIN_DATABASE_URL": clone_url.replace("postgresql://", "postgresql+psycopg://"),
                }
                run(
                    [sys.executable, "-m", "alembic", "-c", str(BACKEND / "alembic.ini"), "upgrade", "head"],
                    env=clone_env,
                    log=log,
                )
                with psycopg.connect(clone_url) as clone:
                    after = fingerprints(clone)
                    assert {k: v for k, v in after.items() if k != "alembic_version"} == {
                        k: v for k, v in before.items() if k != "alembic_version"
                    }
                    assert clone.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0022"
                    policies = clone.execute(
                        "SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid IN ('tenants'::regclass,'users'::regclass)"
                    ).fetchall()
                    assert all(row[1] and row[2] for row in policies)
                metadata["restore_verified"] = True
                metadata["rehearsal_head"] = "0022"
            finally:
                run([str(PG / "pg_ctl"), "-D", str(data), "stop", "-m", "fast"], log=log)
        (folder / "metadata.json").write_text(json.dumps(metadata, indent=2))
        print("Private backup restored and row digests verified; additive migrations rehearsed:", folder)
        if args.rehearse_only:
            print("REHEARSAL ONLY. No live database changes applied.")
            return
        # Recheck the exact live server and unmodified row state immediately before writes.
        with psycopg.connect(admin_url) as conn:
            identity(conn)
            if fingerprints(conn) != before:
                raise RuntimeError("Live state changed during rehearsal; refusing stale repair")
            role = install_lookup_owner(conn, app.username)
        live_env = {
            **os.environ,
            **values,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": os.pathsep.join((str(BACKEND), str(ROOT))),
            "RS_ADMIN_DATABASE_URL": admin_url.replace("postgresql://", "postgresql+psycopg://"),
            "RS_MIGRATOR_DATABASE_URL": admin_url.replace("postgresql://", "postgresql+psycopg://"),
        }
        run(
            [sys.executable, "-m", "alembic", "-c", str(BACKEND / "alembic.ini"), "upgrade", "head"],
            env=live_env,
            log=log,
        )
        with psycopg.connect(admin_url) as conn:
            identity(conn)
            after = fingerprints(conn)
            assert {k: v for k, v in after.items() if k != "alembic_version"} == {
                k: v for k, v in before.items() if k != "alembic_version"
            }
        metadata["applied_lookup_role"] = role
        metadata["live_head"] = "0022"
        (folder / "metadata.json").write_text(json.dumps(metadata, indent=2))
    print("Narrow NOLOGIN lookup ownership and rehearsed migrations applied; all pre-existing row digests preserved.")
    print("Runtime app and original migration owner remain NOBYPASSRLS. No passwords or MFA records changed.")


if __name__ == "__main__":
    main()
