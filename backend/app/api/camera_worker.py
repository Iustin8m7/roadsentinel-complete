"""Worker side of the camera control plane (HMAC-signed, like the rest of ``/api/ingest``).

* ``GET  /api/ingest/cameras/{slug}/config`` - the desired configuration: only the ACTIVE
  version (revision + SHA-256 fingerprint), and only while the camera is runnable. Drafts are
  never delivered. A key scoped to other cameras gets 403 (same as every ingest route).
* ``POST /api/ingest/cameras/{slug}/config/ack`` - the worker reports that it applied
  (``accepted``) or refused (``rejected`` + reason code) a revision. A rejection never changes
  the applied revision, so the last-known-good stays visible.

Heartbeats with telemetry are handled in ``app.api.ingest``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from app.api.ingest import CameraSlug, _camera
from app.core.audit import AuditAction
from app.deps import get_service_principal
from app.schemas.camera_control import AckIn, AckOut, DesiredConfigOut
from app.services import camera_alerts, camera_control
from app.services.camera_control import ControlError
from app.services.ingest_auth import ServicePrincipal

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.get("/cameras/{camera_id}/config", response_model=DesiredConfigOut)
def desired_config(
    camera_id: str = CameraSlug, principal: ServicePrincipal = Depends(get_service_principal)
) -> DesiredConfigOut:
    camera = _camera(principal, camera_id)
    return DesiredConfigOut(**camera_control.desired_for_worker(principal.db, camera))


@router.post("/cameras/{camera_id}/config/ack", response_model=AckOut)
async def ack_config(
    request: Request,
    camera_id: str = CameraSlug,
    principal: ServicePrincipal = Depends(get_service_principal),
) -> AckOut:
    # Parsed here, after the signature check read the (size-capped) body.
    try:
        body = AckIn.model_validate_json(await request.body())
    except ValidationError as exc:
        errors = [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]
        raise HTTPException(422, errors) from None
    return await run_in_threadpool(_ack, principal, camera_id, body)


def _ack(principal: ServicePrincipal, slug: str, body: AckIn) -> AckOut:
    camera = _camera(principal, slug)
    try:
        row = camera_control.record_ack(principal.db, camera, body.model_dump())
    except ControlError as exc:
        principal.db.rollback()
        raise HTTPException(exc.status, exc.detail()) from None
    notice = None
    if body.status == "rejected":  # the worker keeps its last-known-good, but admins must know
        notice = camera_alerts.notify_state(principal.db, camera, row, "config_rejected")
    principal.db.commit()
    camera_alerts.dispatch(notice)
    principal.audit(
        AuditAction.camera_worker_ack,
        resource_type="cameras",
        resource_id=camera.id,
        details={
            "camera": camera.slug,
            "worker_epoch": body.worker_epoch,
            "config_revision": body.revision,
            "fingerprint": body.fingerprint,
            "result": body.status,
            "reason": body.reason_code,
        },
    )
    return AckOut(
        applied_revision=row.applied_revision,
        last_ack_status=row.last_ack_status,
        last_ack_revision=row.last_ack_revision,
    )
