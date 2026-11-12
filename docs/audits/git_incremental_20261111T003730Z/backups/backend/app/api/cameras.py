from __future__ import annotations

import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.audit import AuditAction
from app.core.policy import Permission
from app.deps import Principal, not_found, require, require_fresh_mfa
from app.models import Camera
from app.schemas.ops import CameraIn, CameraOut, CameraUpdateIn, CameraWorkerCommandIn
from app.services import camera_workers
from app.services.camera_discovery import CameraDiscoveryEntry, load_camera_discovery
from app.services.live_preview import live_previews

# GET /api/cameras (the list) is the API.md view, served by app.api.contract.
router = APIRouter(prefix="/api/cameras", tags=["cameras"])


@router.get("/discovery", response_model=list[CameraDiscoveryEntry])
def get_camera_discovery(
    _principal: Principal = Depends(require(Permission.cameras_read)),
) -> list[CameraDiscoveryEntry]:
    """Return the public presentation catalog and independent analytics policy metadata."""
    return list(load_camera_discovery())


def _owned_camera(principal: Principal, camera_id: uuid.UUID) -> Camera:
    camera = principal.db.get(Camera, camera_id)
    if camera is None or camera.tenant_id != principal.tenant_id:
        not_found(principal, "cameras", camera_id)
    return camera


def _persist_worker(principal: Principal, camera: Camera, worker: dict) -> dict:
    info = dict(camera.status_info or {})
    info["worker"] = worker
    camera.status_info = info
    principal.db.commit()
    return worker


@router.post("/provision/ilisesti-dn17", response_model=CameraOut)
def provision_ilisesti_camera(
    principal: Principal = Depends(require(Permission.cameras_manage)),
) -> Camera:
    """Create the one owner-configured operational camera once per tenant."""
    require_fresh_mfa(principal)
    expected = {
        "slug": "ilisesti-dn17",
        "name": "Ilișești DN17",
        "location": "Ilișești, Suceava County, Romania",
        "latitude": 47.6099,
        "longitude": 26.0420,
        "timezone": "Europe/Bucharest",
    }

    def existing_camera() -> Camera | None:
        return principal.db.scalar(
            select(Camera).where(
                Camera.tenant_id == principal.tenant_id,
                Camera.slug == expected["slug"],
            )
        )

    camera = existing_camera()
    if camera is not None:
        if any(getattr(camera, key) != value for key, value in expected.items()):
            raise HTTPException(409, "slug ilisesti-dn17 exists with different camera metadata")
        return camera
    camera = Camera(tenant_id=principal.tenant_id, **expected)
    principal.db.add(camera)
    try:
        principal.db.commit()
    except IntegrityError:
        principal.db.rollback()
        camera = existing_camera()
        if camera is None or any(getattr(camera, key) != value for key, value in expected.items()):
            raise HTTPException(
                409, "camera provision conflicted with another tenant change"
            ) from None
        return camera
    principal.audit(
        AuditAction.camera_created,
        resource_type="cameras",
        resource_id=camera.id,
        details={
            "provisioned_profile": "ilisesti-dn17.yaml",
            "source_candidate_id": "RO-DN17-WCR-001",
        },
    )
    return camera


@router.get("/{camera_id}/worker")
def get_camera_worker(
    camera_id: uuid.UUID, principal: Principal = Depends(require(Permission.cameras_read))
) -> dict:
    camera = _owned_camera(principal, camera_id)
    worker = camera_workers.status(str(principal.tenant_id), str(camera.id), camera.last_seen_at)
    worker["telemetry"] = camera.status_info or {}
    return worker


@router.post("/{camera_id}/worker/start")
def start_camera_worker(
    camera_id: uuid.UUID,
    body: CameraWorkerCommandIn,
    principal: Principal = Depends(require(Permission.cameras_manage)),
) -> dict:
    require_fresh_mfa(principal)
    camera = _owned_camera(principal, camera_id)
    try:
        worker = camera_workers.start(
            str(principal.tenant_id), str(camera.id), camera.slug, body.config_ref
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    worker = _persist_worker(principal, camera, worker)
    principal.audit(
        AuditAction.camera_worker_started,
        resource_type="cameras",
        resource_id=camera.id,
        details={
            "worker_action": "start",
            "desired_state": worker["desired_state"],
            "state": worker["state"],
            "config_ref": body.config_ref,
        },
    )
    return worker


@router.post("/{camera_id}/worker/stop")
def stop_camera_worker(
    camera_id: uuid.UUID, principal: Principal = Depends(require(Permission.cameras_manage))
) -> dict:
    require_fresh_mfa(principal)
    camera = _owned_camera(principal, camera_id)
    worker = camera_workers.stop(str(principal.tenant_id), str(camera.id))
    worker = _persist_worker(principal, camera, worker)
    principal.audit(
        AuditAction.camera_worker_stopped,
        resource_type="cameras",
        resource_id=camera.id,
        details={
            "worker_action": "stop",
            "desired_state": worker["desired_state"],
            "state": worker["state"],
        },
    )
    return worker


@router.post("/{camera_id}/worker/restart")
def restart_camera_worker(
    camera_id: uuid.UUID,
    body: CameraWorkerCommandIn,
    principal: Principal = Depends(require(Permission.cameras_manage)),
) -> dict:
    require_fresh_mfa(principal)
    camera = _owned_camera(principal, camera_id)
    try:
        worker = camera_workers.restart(
            str(principal.tenant_id), str(camera.id), camera.slug, body.config_ref
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    worker = _persist_worker(principal, camera, worker)
    principal.audit(
        AuditAction.camera_worker_restarted,
        resource_type="cameras",
        resource_id=camera.id,
        details={
            "worker_action": "restart",
            "desired_state": worker["desired_state"],
            "state": worker["state"],
            "config_ref": body.config_ref,
        },
    )
    return worker


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(
    camera_id: uuid.UUID, principal: Principal = Depends(require(Permission.cameras_read))
) -> Camera:
    camera = principal.db.get(Camera, camera_id)
    if camera is None:
        not_found(principal, "cameras", camera_id)
    return camera


@router.get("/{camera_id}/preview")
def get_live_preview(
    camera_id: uuid.UUID, principal: Principal = Depends(require(Permission.cameras_read))
) -> Response:
    """Return only the current redacted/annotated frame to an authenticated tenant operator."""
    camera = principal.db.get(Camera, camera_id)
    if camera is None or camera.tenant_id != principal.tenant_id:
        not_found(principal, "cameras", camera_id)
    if camera.lifecycle_state != "legacy":
        from app.services.camera_control import runnable
        if not runnable(principal.db, camera)[0]:
            raise HTTPException(404, "No authorized live preview is available")
    preview = live_previews.get(principal.tenant_id, camera.slug)
    if preview is None:
        raise HTTPException(404, "No fresh annotated frame is available")
    return Response(
        content=preview.jpeg,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, private",
            "X-RS-Captured-At": preview.captured_at.isoformat(),
            "X-RS-Frame-Sequence": str(preview.sequence),
        },
    )


@router.post("", response_model=CameraOut, status_code=201)
def create_camera(
    body: CameraIn, principal: Principal = Depends(require(Permission.cameras_manage))
) -> Camera:
    require_fresh_mfa(principal)
    try:
        ZoneInfo(body.timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise HTTPException(422, "unknown time zone") from None
    camera = Camera(tenant_id=principal.tenant_id, **body.model_dump(exclude_none=True))
    principal.db.add(camera)
    principal.db.commit()
    principal.audit(AuditAction.camera_created, resource_type="cameras", resource_id=camera.id)
    return camera


@router.patch("/{camera_id}", response_model=CameraOut)
def update_camera(
    camera_id: uuid.UUID,
    body: CameraUpdateIn,
    principal: Principal = Depends(require(Permission.cameras_manage)),
) -> Camera:
    """Edit or disable a camera (the slug is the pipeline's identity and never changes). Every
    change is audited with before/after. Zones, rules and calibration live in
    cameras/<id>.yaml and are changed through the repository (docs/RULES.md,
    docs/CALIBRATION.md), not through this API."""
    require_fresh_mfa(principal)
    camera = principal.db.get(Camera, camera_id)
    if camera is None:
        not_found(principal, "cameras", camera_id)
    changes = body.model_dump(exclude_unset=True)
    if "timezone" in changes:
        try:
            ZoneInfo(changes["timezone"])
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            raise HTTPException(422, "unknown time zone") from None
    if not changes:
        raise HTTPException(422, "nothing to change")
    diff = {
        k: {"from": getattr(camera, k), "to": v}
        for k, v in changes.items()
        if getattr(camera, k) != v
    }
    for k, v in changes.items():
        setattr(camera, k, v)
    principal.db.commit()
    principal.audit(
        AuditAction.camera_updated, resource_type="cameras", resource_id=camera.id, details=diff
    )
    return camera
