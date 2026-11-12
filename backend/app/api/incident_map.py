"""Private national map and audited location revisions; existing alert/evidence policy remains."""

import time
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.metrics import metrics
from app.core.policy import Permission, has_permission
from app.core.rate_limit import Limit, get_rate_limiter
from app.deps import Principal, require
from app.models import Camera, CameraConfigVersion, LocationRevision
from app.schemas.geolocation import LocationDecision, LocationInput, MapPage, MapQuery
from app.services import geo_reference, geolocation, incident_map

router = APIRouter(tags=["incident-map"])


def bounded(principal, operation):
    allowed, wait = get_rate_limiter().hit(
        f"map:{operation}:{principal.tenant_id}:{principal.user_id}",
        Limit(120 if operation == "read" else 30, 60),
    )
    if not allowed:
        raise HTTPException(429, "Map request limit", headers={"Retry-After": str(wait)})


@router.get("/api/map/reference")
def reference(principal: Principal = Depends(require(Permission.map_read))):
    bounded(principal, "read")
    return geo_reference.reference()


@router.post("/api/map/incidents/query", response_model=MapPage)
def query(body: MapQuery, principal: Principal = Depends(require(Permission.map_read))):
    bounded(principal, "read")
    at = time.monotonic()
    try:
        value = incident_map.query(principal, body)
        metrics.inc("rs_map_api_requests_total", result="ok")
        return value
    finally:
        metrics.observe("rs_map_query_latency_seconds", time.monotonic() - at)


@router.get("/api/map/cameras")
def cameras(principal: Principal = Depends(require(Permission.location_edit))):
    bounded(principal, "read")
    # Current approved position is an explicit picker choice, not inherited from legacy numeric fields.
    rows = principal.db.execute(
        select(Camera, LocationRevision)
        .join(LocationRevision, LocationRevision.config_version_id == Camera.active_config_id)
        .where(LocationRevision.state == "confirmed")
        .limit(500)
    ).all()
    from app.services.camera_control import evaluate_eligibility, grants_for
    return [
        dict(
            camera_id=str(cam.id),
            name=cam.name,
            source_kind=cam.source_kind,
            is_active=cam.is_active,
            location=geolocation.out(loc),
        )
        for cam, loc in rows
        if cam.is_active
        and not evaluate_eligibility(
            cam,
            grants_for(principal.db, cam.id),
            principal.db.get(CameraConfigVersion, loc.config_version_id),
            datetime.now(UTC),
        )
    ]


@router.get("/api/locations/{kind}/{subject_id}")
def get_location(
    kind: Literal["recording", "alert"],
    subject_id: UUID,
    principal: Principal = Depends(require(Permission.map_read)),
):
    bounded(principal, "read")
    return geolocation.location_state(principal, kind, subject_id)


@router.patch("/api/locations/{kind}/{subject_id}")
def update(
    kind: Literal["recording", "alert"],
    subject_id: UUID,
    body: LocationInput,
    principal: Principal = Depends(require(Permission.location_edit)),
):
    bounded(principal, "write")
    try:
        return geolocation.assign(principal, kind, subject_id, body)
    except HTTPException as error:
        metrics.inc(
            "rs_map_location_updates_total",
            result="conflict" if error.status_code == 409 else "denied",
        )
        principal.audit(
            "location.update.denied",
            resource_type=kind,
            resource_id=subject_id,
            details={"status": error.status_code},
        )
        raise


@router.post("/api/location-proposals/{location_id}/decision")
def decision(
    location_id: UUID,
    body: LocationDecision,
    principal: Principal = Depends(require(Permission.cameras_manage)),
):
    bounded(principal, "write")
    return geolocation.decide(principal, location_id, body)

@router.get("/api/locations/{kind}/{subject_id}/history")
def location_history(
    kind: Literal["recording", "alert"],
    subject_id: UUID,
    principal: Principal = Depends(require(Permission.map_read)),
):
    """Append-only revisions, protected by the same subject and RLS checks as current state."""
    bounded(principal, "read")
    geolocation.subject(principal, kind, subject_id)
    from sqlalchemy import func
    column = getattr(LocationRevision, kind + "_id")
    rows = principal.db.scalars(
        select(LocationRevision)
        .where(column == subject_id)
        .order_by(LocationRevision.revision.desc())
        .limit(100)
    ).all()
    return [geolocation.out(row) for row in rows]


@router.get("/api/map/incidents/{incident_id}")
def incident_detail(
    incident_id: UUID,
    principal: Principal = Depends(require(Permission.map_read)),
):
    bounded(principal, "read")
    from app.services.incident_map import projection, summary
    visible = projection(principal)
    row = principal.db.execute(
        select(visible).where(visible.c.id == incident_id)
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "Incident not found")
    if row["is_demo"] and not has_permission(principal.role, Permission.map_demo_read):
        raise HTTPException(404, "Incident not found")
    return summary(row, principal)


@router.get("/api/map/alerts/{number}")
def incident_by_alert_number(
    number: int,
    principal: Principal = Depends(require(Permission.map_read)),
):
    bounded(principal, "read")
    from app.services.incident_map import projection, summary
    visible = projection(principal)
    row = principal.db.execute(
        select(visible).where(visible.c.number == number)
    ).mappings().one_or_none()
    if row is None or (row["is_demo"] and not has_permission(principal.role, Permission.map_demo_read)):
        raise HTTPException(404, "Incident not found")
    return summary(row, principal)

@router.get("/api/map/cameras/{camera_id}/location-history")
def camera_location_history(
    camera_id: UUID,
    principal: Principal = Depends(require(Permission.cameras_read)),
):
    bounded(principal, "read")
    geolocation.subject(principal, "camera", camera_id)
    rows = principal.db.scalars(
        select(LocationRevision)
        .where(LocationRevision.camera_id == camera_id)
        .order_by(LocationRevision.revision.desc())
        .limit(100)
    ).all()
    return [geolocation.out(row) for row in rows]
