"""Liveness / readiness checks and bounded operational counters.

* Liveness answers from the process alone (no database, no storage): a restart is the only fix
  for a process that cannot answer it.
* Readiness checks the dependencies a request needs: the database (short connect and statement
  timeouts), the schema revision (must equal the code's Alembic head) and evidence storage
  (local directory writable, or S3 bucket reachable). Each check reports its own status; the
  overall answer is ready only when every check is ok. Nothing here is hardcoded green.

Readiness is called unauthenticated (load balancers), so ``app/api/health.py`` returns only the
overall status to anonymous callers. The full body below (statuses, revision ids, exception
class names, storage backend) goes to the metrics token or a tenant admin / auditor; it never
carries URLs, bucket names, paths or messages that could contain credentials.
"""

from __future__ import annotations

import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, pool, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from app.config import get_settings
from app.core import metrics

DB_TIMEOUT_SECONDS = 2
STORAGE_TIMEOUT_SECONDS = 2
# Readiness is unauthenticated: cache the result briefly so probes cannot hammer the database
# or the bucket. Short enough that a dependency outage shows up within seconds.
CACHE_SECONDS = 2.0
LOW_DISK_BYTES = 1024**3  # warn below 1 GiB free ...
LOW_DISK_RATIO = 0.05  # ... or below 5 % free

OK, ERROR, WARNING = "ok", "error", "warning"
STARTED_AT = metrics.STARTED_AT  # one process start time for ops status and /api/metrics


@dataclass
class Check:
    status: str
    detail: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"status": self.status, **self.data}
        if self.detail:
            out["detail"] = self.detail
        return out


# --------------------------------------------------------------------------- migrations


@lru_cache
def code_heads() -> tuple[str, ...]:
    """Alembic head revision(s) shipped with this code (read from the migration scripts)."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    return tuple(sorted(ScriptDirectory.from_config(Config(str(ini))).get_heads()))


# --------------------------------------------------------------------------- database


@lru_cache
def probe_engine() -> Engine:
    """A separate, unpooled engine with short timeouts: each probe really connects, and a hung
    database answers 'not ready' within seconds instead of blocking the probe."""
    return create_engine(
        get_settings().database_url.get_secret_value(),
        poolclass=pool.NullPool,
        connect_args={
            "connect_timeout": DB_TIMEOUT_SECONDS,
            "options": f"-c statement_timeout={DB_TIMEOUT_SECONDS * 1000}",
        },
    )


def check_database(engine: Engine | None = None) -> tuple[Check, Check]:
    """(database, migrations). The revision is read with the runtime role (granted read-only
    on ``alembic_version`` by ``alembic/env.py``)."""
    engine = engine or probe_engine()
    started = time.monotonic()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            latency_ms = round((time.monotonic() - started) * 1000, 1)
            db = Check(OK, data={"latency_ms": latency_ms})
            try:
                current = tuple(
                    sorted(
                        r[0] for r in conn.execute(text("SELECT version_num FROM alembic_version"))
                    )
                )
            except DBAPIError as exc:
                return db, Check(
                    ERROR,
                    "schema revision not readable (run: python -m app.cli migrate)",
                    {"error": type(exc.orig).__name__ if exc.orig else type(exc).__name__},
                )
    except SQLAlchemyError as exc:
        orig = getattr(exc, "orig", None)
        name = type(orig).__name__ if orig is not None else type(exc).__name__
        return (
            Check(ERROR, "database unreachable", {"error": name}),
            Check(ERROR, "not checked: database unreachable"),
        )
    heads = code_heads()
    data = {"current": list(current), "expected": list(heads)}
    if current == heads:
        return db, Check(OK, data=data)
    if not current:
        return db, Check(ERROR, "database is not migrated", data)
    return db, Check(ERROR, "schema revision differs from the code's migration head", data)


# --------------------------------------------------------------------------- evidence storage


def _check_local(root: Path) -> Check:
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        probe = root / f".rs-ready-{uuid.uuid4().hex}"
        probe.write_bytes(b"ok")
        probe.unlink()
    except OSError as exc:
        return Check(
            ERROR,
            "evidence directory not writable",
            {"backend": "local", "error": type(exc).__name__},
        )
    usage = shutil.disk_usage(root)
    data: dict[str, Any] = {
        "backend": "local",
        "free_bytes": usage.free,
        "total_bytes": usage.total,
    }
    if usage.free < LOW_DISK_BYTES or usage.free < usage.total * LOW_DISK_RATIO:
        return Check(WARNING, "low disk space for evidence", data)
    return Check(OK, data=data)


def _check_s3(bucket: str) -> Check:
    try:
        import boto3
        from botocore.config import Config as BotoConfig
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:  # pragma: no cover - boto3 is a pinned runtime dependency
        return Check(ERROR, "S3 client library not installed", {"backend": "s3"})
    s = get_settings()
    client = boto3.client(
        "s3",
        endpoint_url=s.evidence_s3_endpoint,
        region_name=s.evidence_s3_region,
        aws_access_key_id=(
            s.evidence_s3_access_key_id.get_secret_value() if s.evidence_s3_access_key_id else None
        ),
        aws_secret_access_key=(
            s.evidence_s3_secret_access_key.get_secret_value()
            if s.evidence_s3_secret_access_key
            else None
        ),
        config=BotoConfig(
            connect_timeout=STORAGE_TIMEOUT_SECONDS,
            read_timeout=STORAGE_TIMEOUT_SECONDS,
            retries={"max_attempts": 1, "mode": "standard"},
        ),
    )
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", "unknown"))[:32]
        detail = (
            "bucket access denied (check the evidence S3 credentials)"
            if code in {"403", "AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}
            else "bucket not reachable"
        )
        return Check(ERROR, detail, {"backend": "s3", "error": code})
    except BotoCoreError as exc:
        return Check(ERROR, "bucket not reachable", {"backend": "s3", "error": type(exc).__name__})
    return Check(OK, data={"backend": "s3"})


def check_storage() -> Check:
    s = get_settings()
    if s.evidence_s3_bucket:
        return _check_s3(s.evidence_s3_bucket)
    return _check_local(s.evidence_dir.resolve())


# --------------------------------------------------------------------------- readiness


_cache_lock = threading.Lock()
_cache: tuple[float, bool, dict[str, Any]] | None = None


def clear_cache() -> None:
    global _cache
    with _cache_lock:
        _cache = None


def readiness() -> tuple[bool, dict[str, Any]]:
    """(ready, body). Storage free space is reported only to authenticated callers."""
    global _cache
    with _cache_lock:
        if _cache is not None and time.monotonic() - _cache[0] < CACHE_SECONDS:
            return _cache[1], _cache[2]
    db, migrations = check_database()
    storage = check_storage()
    storage_public = storage.as_dict()
    storage_public.pop("free_bytes", None)
    storage_public.pop("total_bytes", None)
    checks = {
        "database": db.as_dict(),
        "migrations": migrations.as_dict(),
        "evidence_storage": storage_public,
    }
    ready = all(c.status in (OK, WARNING) for c in (db, migrations, storage))
    body = {"status": "ready" if ready else "not_ready", "checks": checks}
    with _cache_lock:
        _cache = (time.monotonic(), ready, body)
    return ready, body
