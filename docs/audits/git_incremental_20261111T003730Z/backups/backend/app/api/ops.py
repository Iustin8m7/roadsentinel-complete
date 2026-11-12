"""Operational endpoints: readiness, process metrics (token), and a per-tenant status page."""

from __future__ import annotations

import hmac
from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select, text

from app.config import get_settings
from app.core.metrics import metrics
from app.core.policy import Permission
from app.db import get_engine
from app.deps import Principal, require
from app.models import Alert, Camera, Evidence

router = APIRouter(tags=["ops"])

STALE_AFTER_S = 120  # the pipeline sends a heartbeat every 30 s


@router.get("/api/ready")
def ready() -> dict[str, object]:
    """Readiness: the database answers and the schema is migrated (alembic_version present)."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        raise HTTPException(503, "not ready") from None
    if not version:
        raise HTTPException(503, "not migrated")
    return {"status": "ready", "schema": version}


@router.get("/api/metrics", include_in_schema=False)
def prometheus(authorization: str | None = Header(default=None)) -> Response:
    token = get_settings().metrics_token
    if token is None or not token.get_secret_value():
        raise HTTPException(404, "Not found")  # disabled unless configured
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not hmac.compare_digest(supplied.encode(), token.get_secret_value().encode()):
        raise HTTPException(401, "Unauthorized")
    return Response(metrics.render(), media_type="text/plain; version=0.0.4")


class CameraStatus(BaseModel):
    slug: str
    name: str
    is_active: bool
    last_seen_age_s: int | None
    stale: bool
    fps: float | None
    unsupported_rules: list[str]


class OpsStatus(BaseModel):
    generated_at: datetime
    alerts_24h: int
    alerts_24h_by_type: dict[str, int]
    new_unreviewed: int
    evidence_files: int
    evidence_purged: int
    cameras: list[CameraStatus]
    alerts_that_need_attention: list[str]


@router.get("/api/ops/status", response_model=OpsStatus)
def ops_status(principal: Principal = Depends(require(Permission.retention_manage))) -> OpsStatus:
    """What an on-call person needs at a glance, for this tenant only. Page a human when a
    camera is stale, unreviewed alerts pile up or storage errors appear (docs/OPERATIONS.md)."""
    now = datetime.now(UTC)
    since = now - timedelta(hours=24)
    rows = principal.db.execute(
        select(Alert.event_type, Alert.status).where(
            Alert.created_at >= since, Alert.superseded_at.is_(None)
        )
    ).all()
    by_type = Counter(r[0] for r in rows)
    new = sum(1 for r in rows if r[1].value == "new")
    cams = []
    for c in principal.db.scalars(select(Camera).order_by(Camera.name)):
        age = int((now - c.last_seen_at).total_seconds()) if c.last_seen_at else None
        info = c.status_info or {}
        cams.append(
            CameraStatus(
                slug=c.slug,
                name=c.name,
                is_active=c.is_active,
                last_seen_age_s=age,
                stale=c.is_active and (age is None or age > STALE_AFTER_S),
                fps=info.get("fps"),
                unsupported_rules=sorted(
                    k for k, v in (info.get("rules") or {}).items() if not v.get("supported")
                ),
            )
        )
    files = (
        principal.db.scalar(
            select(text("count(*)")).select_from(Evidence).where(Evidence.purged_at.is_(None))
        )
        or 0
    )
    purged = (
        principal.db.scalar(
            select(text("count(*)")).select_from(Evidence).where(Evidence.purged_at.is_not(None))
        )
        or 0
    )
    attention = [
        (
            f"camera {c.slug}: no heartbeat for {c.last_seen_age_s} s"
            if c.last_seen_age_s
            else f"camera {c.slug}: never seen"
        )
        for c in cams
        if c.stale
    ]
    if new > 50:
        attention.append(f"{new} unreviewed alerts in the last 24 h")
    return OpsStatus(
        generated_at=now,
        alerts_24h=len(rows),
        alerts_24h_by_type=dict(by_type),
        new_unreviewed=new,
        evidence_files=int(files),
        evidence_purged=int(purged),
        cameras=cams,
        alerts_that_need_attention=attention,
    )
