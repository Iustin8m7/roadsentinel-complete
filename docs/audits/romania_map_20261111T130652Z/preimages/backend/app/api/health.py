"""Health surfaces.

``GET /api/health``        legacy combined check (kept: deploy smoke test and image HEALTHCHECK)
``GET /api/health/live``   liveness: the process answers; no external dependency is touched
``GET /api/health/ready``  readiness: database, schema revision, evidence storage (503 if not).
                           Anonymous callers get the overall status only; the per-component
                           checks need the metrics token or a tenant admin / auditor session
``GET /api/ops/status``    authenticated, tenant-scoped operational counters (tenant admin,
                           auditor): bounded numbers only, no camera URLs, plates or people
``GET /api/metrics``       Prometheus text, ``Authorization: Bearer <RS_METRICS_TOKEN>``; 404
                           when no token is configured
"""

from __future__ import annotations

import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import metrics
from app.core.http import ACCESS, cookie_name
from app.core.policy import Permission, has_permission
from app.deps import Principal, get_principal, require
from app.models import Alert, AlertStatus, AuditLog, Camera, Evidence, User
from app.services import health

router = APIRouter(tags=["health"])

# A camera counts as "recently seen" if the pipeline sent a heartbeat or event within this
# window. It is a counter for operators, not a LIVE badge (worker health belongs to the
# camera control plane).
RECENT_HEARTBEAT = timedelta(seconds=120)


@router.get("/api/health/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


def metrics_token_ok(request: Request) -> bool:
    """``Authorization: Bearer <RS_METRICS_TOKEN>``, compared in constant time."""
    expected = get_settings().metrics_token_value
    if expected is None:
        return False
    scheme, _, supplied = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not supplied.strip():
        return False
    return secrets.compare_digest(supplied.strip().encode(), expected.encode())


def _staff_session(request: Request) -> bool:
    """A signed-in tenant admin or auditor (``audit:read``). Uses the readiness probe engine
    (2 s timeouts), so a hung database cannot hold the probe; any failure means anonymous."""
    if not request.cookies.get(cookie_name(ACCESS)):
        return False
    db = Session(bind=health.probe_engine())
    try:
        principal = get_principal(request, db)
        return has_permission(principal.role, Permission.audit_read)
    except Exception:
        return False
    finally:
        db.close()


@router.get("/api/health/ready")
async def ready(request: Request) -> JSONResponse:
    ok, body = await run_in_threadpool(health.readiness)
    detailed = metrics_token_ok(request) or await run_in_threadpool(_staff_session, request)
    # Anonymous callers (load balancers, the public internet through the gateway) learn only
    # ready / not ready: revisions, driver error classes and the storage backend stay private.
    return JSONResponse(
        body if detailed else {"status": body["status"]}, status_code=200 if ok else 503
    )


@router.get("/api/metrics/detailed", include_in_schema=False)
def metrics_text(request: Request) -> PlainTextResponse:
    if get_settings().metrics_token_value is None:
        raise HTTPException(404, "Not Found")
    if not metrics_token_ok(request):
        raise HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    return PlainTextResponse(
        metrics.render_prometheus(), media_type="text/plain; version=0.0.4; charset=utf-8"
    )


def _age_seconds(ts: datetime | None, now: datetime) -> int | None:
    return None if ts is None else max(0, int((now - ts).total_seconds()))


@router.get("/api/ops/reliability")
def ops_status(principal: Principal = Depends(require(Permission.audit_read))) -> dict[str, Any]:
    """Counters for the caller's tenant only (RLS plus an explicit tenant filter)."""
    db, tid = principal.db, principal.tenant_id
    now = datetime.now(UTC)

    by_status = {s.value: 0 for s in AlertStatus}
    for status, count in db.execute(
        select(Alert.status, func.count()).where(Alert.tenant_id == tid).group_by(Alert.status)
    ):
        by_status[AlertStatus(status).value] = int(count)
    oldest_new, last_alert = db.execute(
        select(
            func.min(Alert.detected_at).filter(Alert.status == AlertStatus.new),
            func.max(Alert.created_at),
        ).where(Alert.tenant_id == tid)
    ).one()

    cutoff = now - RECENT_HEARTBEAT
    cams = db.execute(
        select(
            func.count(),
            func.count().filter(Camera.is_active),
            func.count().filter(Camera.last_seen_at >= cutoff),
            func.count().filter(Camera.last_seen_at.is_(None)),
            func.max(Camera.last_seen_at),
        ).where(Camera.tenant_id == tid)
    ).one()

    evidence_count = db.scalar(select(func.count()).where(Evidence.tenant_id == tid)) or 0
    audit_len, audit_last = db.execute(
        select(func.max(AuditLog.seq), func.max(AuditLog.ts)).where(AuditLog.tenant_id == tid)
    ).one()
    users = db.execute(
        select(
            func.count().filter(User.is_active),
            func.count().filter(User.is_active & User.mfa_exempt),
        ).where(User.tenant_id == tid)
    ).one()

    storage = health.check_storage()
    _, migrations = health.check_database()
    return {
        "generated_at": now.isoformat(),
        "process": {"uptime_seconds": int(time.time() - health.STARTED_AT)},
        "alerts": {
            "by_status": by_status,
            "queue_new": by_status[AlertStatus.new.value],
            "oldest_new_age_seconds": _age_seconds(oldest_new, now),
            "last_ingested_age_seconds": _age_seconds(last_alert, now),
        },
        "cameras": {
            "total": int(cams[0]),
            "active": int(cams[1]),
            "seen_last_120s": int(cams[2]),
            "never_seen": int(cams[3]),
            "newest_heartbeat_age_seconds": _age_seconds(cams[4], now),
        },
        "evidence": {"count": int(evidence_count), "storage": storage.as_dict()},
        "audit": {
            "chain_length": int(audit_len or 0),
            "last_entry_age_seconds": _age_seconds(audit_last, now),
        },
        "users": {"active": int(users[0]), "mfa_exempt_active": int(users[1])},
        "schema": migrations.as_dict(),
    }
