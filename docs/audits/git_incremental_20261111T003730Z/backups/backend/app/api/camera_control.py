"""Camera control plane for administrators and read-only status for operators/auditors.

* Reads need ``cameras:status_read`` (tenant admin, operator, auditor); every mutation needs
  ``cameras:manage`` (tenant admin) and, where policy says so, a second admin (four-eyes).
* Every camera mutation carries ``expected_revision`` (compare-and-swap on ``cameras.revision``
  under a row lock): a stale client gets 409 ``revision_conflict``.
* Cross-tenant ids answer 404 exactly like missing ones (the probe is audited).
* Refusals (403/409) carry ``{"detail": {"code", "message", ...}}`` and are audited.
* Nothing here returns, logs or audits the source URL; only its host-level display form.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.core.audit import AuditAction
from app.core.policy import Permission
from app.deps import Principal, not_found, require
from app.models import Camera, CameraConfigVersion, CameraHealthEvent, CameraSourceGrant
from app.schemas import camera_control as s
from app.services import camera_config as cc
from app.services import camera_control as ctl
from app.services.camera_control import ControlError

router = APIRouter(prefix="/api/camera-control", tags=["camera-control"])

READ = Depends(require(Permission.cameras_status_read))
MANAGE = Depends(require(Permission.cameras_manage))


# --------------------------------------------------------------------------- helpers


def _camera(principal: Principal, camera_id: uuid.UUID, *, lock: bool = False) -> Camera:
    db = principal.db
    camera = ctl.lock_camera(db, camera_id) if lock else db.get(Camera, camera_id)
    if camera is None:
        not_found(principal, "cameras", camera_id)
    return camera


def _version(principal: Principal, camera: Camera, version_id: uuid.UUID) -> CameraConfigVersion:
    version = principal.db.get(CameraConfigVersion, version_id)
    if version is None or version.camera_id != camera.id:
        raise HTTPException(404, "Not found")
    return version


@contextmanager
def _guard(principal: Principal, camera: Camera, action: str) -> Iterator[None]:
    """Turn a refused operation into an audited 4xx with a stable error code."""
    camera_id = camera.id
    try:
        yield
    except ControlError as exc:
        principal.db.rollback()
        if exc.status in (403, 409):
            principal.audit(
                AuditAction.camera_control_refused,
                resource_type="cameras",
                resource_id=camera_id,
                details={"action": action, "refusal": exc.code},
            )
        raise HTTPException(exc.status, exc.detail()) from None


def _summary(principal: Principal, camera: Camera) -> s.ControlSummary:
    row = ctl.worker_status(principal.db, camera.id)
    return s.ControlSummary(
        id=camera.id,
        slug=camera.slug,
        name=camera.name,
        location=camera.location,
        timezone=camera.timezone,
        lifecycle_state=camera.lifecycle_state,
        source_kind=camera.source_kind,
        source_display=camera.source_display,
        source_has_credentials=camera.source_has_credentials,
        desired_enabled=camera.desired_enabled,
        revision=camera.revision,
        active_version_id=camera.active_config_id,
        disabled_reason=camera.disabled_reason,
        enable_requested_by=camera.enable_requested_by,
        enable_requested_at=camera.enable_requested_at,
        runtime=s.RuntimeOut(**ctl.derive_status(principal.db, camera, row)),
    )


def _eligibility(
    principal: Principal, camera: Camera, version: CameraConfigVersion | None
) -> s.EligibilityOut:
    unmet = ctl.evaluate_eligibility(camera, ctl.grants_for(principal.db, camera.id), version)
    return s.EligibilityOut(
        eligible=not unmet,
        unmet=[s.UnmetOut(**u.as_dict()) for u in unmet],
        version_id=version.id if version else None,
        evaluated_at=datetime.now(UTC),
    )


def _detail(principal: Principal, camera: Camera) -> s.ControlDetail:
    row = ctl.worker_status(principal.db, camera.id)
    return s.ControlDetail(
        **_summary(principal, camera).model_dump(),
        worker=s.WorkerOut.model_validate(row) if row else None,
        grants=[s.GrantOut.model_validate(g) for g in ctl.grants_for(principal.db, camera.id)],
        eligibility=_eligibility(principal, camera, ctl.active_version(principal.db, camera)),
        unsupported_actions=ctl.UNSUPPORTED_ACTIONS,
    )


def _audit_camera(
    principal: Principal, action: AuditAction, camera: Camera, **details: Any
) -> None:
    principal.audit(
        action,
        resource_type="cameras",
        resource_id=camera.id,
        details={"camera": camera.slug, "revision": camera.revision, **details},
    )


# --------------------------------------------------------------------------- reads


@router.get("/cameras", response_model=list[s.ControlSummary])
def list_cameras(principal: Principal = READ) -> list[s.ControlSummary]:
    cameras = principal.db.scalars(select(Camera).order_by(Camera.name, Camera.slug))
    return [_summary(principal, c) for c in cameras]


@router.get("/cameras/{camera_id}", response_model=s.ControlDetail)
def get_camera(camera_id: uuid.UUID, principal: Principal = READ) -> s.ControlDetail:
    return _detail(principal, _camera(principal, camera_id))


@router.get("/cameras/{camera_id}/versions", response_model=list[s.VersionSummary])
def list_versions(camera_id: uuid.UUID, principal: Principal = READ) -> list[CameraConfigVersion]:
    camera = _camera(principal, camera_id)
    return list(
        principal.db.scalars(
            select(CameraConfigVersion)
            .where(CameraConfigVersion.camera_id == camera.id)
            .order_by(CameraConfigVersion.revision.desc())
        )
    )


@router.get("/cameras/{camera_id}/versions/{version_id}", response_model=s.VersionOut)
def get_version(
    camera_id: uuid.UUID, version_id: uuid.UUID, principal: Principal = READ
) -> CameraConfigVersion:
    return _version(principal, _camera(principal, camera_id), version_id)


@router.get("/cameras/{camera_id}/versions/{version_id}/diff", response_model=s.DiffOut)
def diff_version(
    camera_id: uuid.UUID,
    version_id: uuid.UUID,
    against: uuid.UUID | None = None,
    principal: Principal = READ,
) -> s.DiffOut:
    """Canonical diff of ``version_id`` against ``against`` (default: the active version)."""
    camera = _camera(principal, camera_id)
    target = _version(principal, camera, version_id)
    base = (
        _version(principal, camera, against)
        if against
        else ctl.active_version(principal.db, camera)
    )
    return s.DiffOut(
        from_version_id=base.id if base else None,
        from_revision=base.revision if base else None,
        to_version_id=target.id,
        to_revision=target.revision,
        changes=cc.diff(base.config if base else None, target.config),
    )


@router.get("/cameras/{camera_id}/grants", response_model=list[s.GrantOut])
def list_grants(camera_id: uuid.UUID, principal: Principal = READ) -> list[CameraSourceGrant]:
    return ctl.grants_for(principal.db, _camera(principal, camera_id).id)


@router.get("/cameras/{camera_id}/eligibility", response_model=s.EligibilityOut)
def eligibility(
    camera_id: uuid.UUID, version_id: uuid.UUID | None = None, principal: Principal = READ
) -> s.EligibilityOut:
    """Dry run: every unmet requirement for processing, without contacting the source."""
    camera = _camera(principal, camera_id)
    version = (
        _version(principal, camera, version_id)
        if version_id
        else ctl.active_version(principal.db, camera)
    )
    return _eligibility(principal, camera, version)


@router.get("/cameras/{camera_id}/health", response_model=list[s.HealthEventOut])
def health_history(
    camera_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=ctl.HEALTH_HISTORY_CAP),
    principal: Principal = READ,
) -> list[CameraHealthEvent]:
    camera = _camera(principal, camera_id)
    return list(
        principal.db.scalars(
            select(CameraHealthEvent)
            .where(CameraHealthEvent.camera_id == camera.id)
            .order_by(CameraHealthEvent.at.desc(), CameraHealthEvent.id.desc())
            .limit(limit)
        )
    )


# --------------------------------------------------------------------------- camera mutations


@router.patch("/cameras/{camera_id}", response_model=s.ControlSummary)
def update_camera(
    camera_id: uuid.UUID, body: s.CameraPatch, principal: Principal = MANAGE
) -> s.ControlSummary:
    """Non-secret metadata. The slug (stable identity) cannot be changed here."""
    camera = _camera(principal, camera_id, lock=True)
    changes = body.model_dump(exclude={"expected_revision", "reason"}, exclude_unset=True)
    if "timezone" in changes:
        try:
            ZoneInfo(changes["timezone"] or "")
        except (ZoneInfoNotFoundError, ValueError):
            raise HTTPException(
                422, {"code": "invalid_timezone", "message": "Unknown timezone"}
            ) from None
    for key in ("name", "location", "timezone"):
        if key in changes and changes[key] is None:
            raise HTTPException(422, {"code": "required", "message": f"{key} cannot be null"})
    with _guard(principal, camera, "update"):
        ctl._check_revision(camera, body.expected_revision)
    before = {k: getattr(camera, k) for k in changes}
    for key, value in changes.items():
        setattr(camera, key, value)
    camera.revision += 1
    principal.db.commit()
    _audit_camera(
        principal,
        AuditAction.camera_updated,
        camera,
        before=before,
        after=changes,
        reason=body.reason,
    )
    return _summary(principal, camera)


@router.post("/cameras/{camera_id}/lifecycle", response_model=s.ControlSummary)
def change_lifecycle(
    camera_id: uuid.UUID, body: s.LifecycleIn, principal: Principal = MANAGE
) -> s.ControlSummary:
    """Register a discovered camera or adopt a legacy one into the control plane. Neither
    enables processing (an adopted legacy camera stops accepting evidence until activated)."""
    camera = _camera(principal, camera_id, lock=True)
    with _guard(principal, camera, "lifecycle"):
        before = ctl.transition_lifecycle(camera, body.to, body.expected_revision)
        ctl.add_event(principal.db, camera, "control", reason_code=f"lifecycle:{body.to}")
        principal.db.commit()
    _audit_camera(
        principal,
        AuditAction.camera_lifecycle_changed,
        camera,
        before=before,
        after=body.to,
        reason=body.reason,
    )
    return _summary(principal, camera)


@router.post("/cameras/{camera_id}/source", response_model=s.ControlSummary)
def set_source(
    camera_id: uuid.UUID, body: s.SourceIn, principal: Principal = MANAGE
) -> s.ControlSummary:
    camera = _camera(principal, camera_id, lock=True)
    with _guard(principal, camera, "source"):
        details = ctl.set_source(
            principal.db,
            principal.keyring,
            camera,
            kind=body.kind,
            url=body.url,
            expected_revision=body.expected_revision,
        )
        ctl.add_event(principal.db, camera, "control", reason_code="source_changed")
        principal.db.commit()
    _audit_camera(principal, AuditAction.camera_source_set, camera, **details, reason=body.reason)
    return _summary(principal, camera)


def _simple_action(
    principal: Principal,
    camera_id: uuid.UUID,
    body: s.RevisionedAction,
    name: str,
    action: AuditAction,
) -> s.ControlSummary:
    camera = _camera(principal, camera_id, lock=True)
    before = {"lifecycle": camera.lifecycle_state, "desired_enabled": camera.desired_enabled}
    with _guard(principal, camera, name):
        rev = body.expected_revision
        if name == "pause":
            ctl.pause(camera, rev)
        elif name == "resume":
            ctl.resume(principal.db, camera, rev)
        elif name == "disable":
            ctl.disable(camera, rev, body.reason)
        elif name == "enable_request":
            ctl.request_enable(camera, principal.user_id, rev)
        else:
            ctl.confirm_enable(principal.db, camera, principal.user_id, rev)
        ctl.add_event(principal.db, camera, "control", reason_code=name)
        principal.db.commit()
    after = {"lifecycle": camera.lifecycle_state, "desired_enabled": camera.desired_enabled}
    _audit_camera(principal, action, camera, before=before, after=after, reason=body.reason)
    return _summary(principal, camera)


@router.post("/cameras/{camera_id}/pause", response_model=s.ControlSummary)
def pause(
    camera_id: uuid.UUID, body: s.RevisionedAction, principal: Principal = MANAGE
) -> s.ControlSummary:
    return _simple_action(principal, camera_id, body, "pause", AuditAction.camera_paused)


@router.post("/cameras/{camera_id}/resume", response_model=s.ControlSummary)
def resume(
    camera_id: uuid.UUID, body: s.RevisionedAction, principal: Principal = MANAGE
) -> s.ControlSummary:
    return _simple_action(principal, camera_id, body, "resume", AuditAction.camera_resumed)


@router.post("/cameras/{camera_id}/disable", response_model=s.ControlSummary)
def disable(
    camera_id: uuid.UUID, body: s.RevisionedAction, principal: Principal = MANAGE
) -> s.ControlSummary:
    return _simple_action(principal, camera_id, body, "disable", AuditAction.camera_disabled)


@router.post("/cameras/{camera_id}/enable-request", response_model=s.ControlSummary)
def enable_request(
    camera_id: uuid.UUID, body: s.RevisionedAction, principal: Principal = MANAGE
) -> s.ControlSummary:
    return _simple_action(
        principal, camera_id, body, "enable_request", AuditAction.camera_enable_requested
    )


@router.post("/cameras/{camera_id}/enable", response_model=s.ControlSummary)
def enable(
    camera_id: uuid.UUID, body: s.RevisionedAction, principal: Principal = MANAGE
) -> s.ControlSummary:
    """Second admin confirms re-enabling a disabled camera (four-eyes)."""
    return _simple_action(principal, camera_id, body, "enable", AuditAction.camera_enabled)


# --------------------------------------------------------------------------- grants


@router.post("/cameras/{camera_id}/grants", response_model=s.GrantOut, status_code=201)
def create_grant(
    camera_id: uuid.UUID, body: s.GrantIn, principal: Principal = MANAGE
) -> CameraSourceGrant:
    camera = _camera(principal, camera_id)
    if body.valid_until <= body.valid_from:
        raise HTTPException(
            422, {"code": "invalid_validity", "message": "valid_until must be after valid_from"}
        )
    grant = CameraSourceGrant(
        tenant_id=principal.tenant_id,
        camera_id=camera.id,
        reviewed_by=principal.user_id,
        status="active",
        **body.model_dump(),
    )
    principal.db.add(grant)
    principal.db.flush()
    ctl.add_event(principal.db, camera, "control", reason_code="grant_created")
    principal.db.commit()
    _audit_camera(
        principal,
        AuditAction.camera_grant_created,
        camera,
        grant_id=str(grant.id),
        basis=grant.basis,
        basis_reference=grant.basis_reference,
        capture_method=grant.capture_method,
        valid_from=grant.valid_from.isoformat(),
        valid_until=grant.valid_until.isoformat(),
    )
    return grant


@router.post("/cameras/{camera_id}/grants/{grant_id}/revoke", response_model=s.GrantOut)
def revoke_grant(
    camera_id: uuid.UUID, grant_id: uuid.UUID, body: s.RevokeIn, principal: Principal = MANAGE
) -> CameraSourceGrant:
    camera = _camera(principal, camera_id)
    grant = principal.db.get(CameraSourceGrant, grant_id)
    if grant is None or grant.camera_id != camera.id:
        raise HTTPException(404, "Not found")
    if grant.status != "revoked":
        grant.status, grant.revoked_at = "revoked", datetime.now(UTC)
        grant.revoked_by, grant.revocation_reason = principal.user_id, body.reason
        ctl.add_event(principal.db, camera, "control", reason_code="grant_revoked")
        principal.db.commit()
        _audit_camera(
            principal,
            AuditAction.camera_grant_revoked,
            camera,
            grant_id=str(grant.id),
            reason=body.reason,
        )
    return grant


# --------------------------------------------------------------------------- config versions


@router.post("/cameras/{camera_id}/config/validate", response_model=s.ValidationOut)
def validate_config(
    camera_id: uuid.UUID, body: s.ValidateIn, principal: Principal = MANAGE
) -> s.ValidationOut:
    """Stateless dry run for editors: nothing is stored, no capture is started."""
    _camera(principal, camera_id)
    errors = cc.validate(body.config)
    return s.ValidationOut(
        valid=not errors,
        errors=[s.ConfigErrorOut(**e.as_dict()) for e in errors],
        fingerprint=cc.fingerprint(body.config),
        min_fps=cc.min_fps(body.config),
    )


@router.post("/cameras/{camera_id}/versions", response_model=s.VersionOut, status_code=201)
def create_version(
    camera_id: uuid.UUID, body: s.DraftIn, principal: Principal = MANAGE
) -> CameraConfigVersion:
    """Store a DRAFT (immutable snapshot) with its validation result; never starts capture."""
    if len(json.dumps(body.config, default=str)) > cc.MAX_CONFIG_BYTES:
        raise HTTPException(413, {"code": "too_large", "message": "Configuration too large"})
    if not cc.storable(body.config):
        raise HTTPException(
            422, {"code": "invalid_config", "message": "NaN, Infinity and NUL are not allowed"}
        )
    camera = _camera(principal, camera_id, lock=True)
    with _guard(principal, camera, "draft"):
        version = ctl.create_version(
            principal.db, camera, body.config, principal.user_id, body.reason
        )
        principal.db.commit()
    principal.audit(
        AuditAction.camera_config_drafted,
        resource_type="cameras",
        resource_id=camera.id,
        details={
            "camera": camera.slug,
            "version_id": str(version.id),
            "config_revision": version.revision,
            "fingerprint": version.fingerprint,
            "error_count": len(version.validation_errors),
            "reason": body.reason,
        },
    )
    return version


def _version_action(
    principal: Principal,
    camera_id: uuid.UUID,
    version_id: uuid.UUID,
    name: str,
    action: AuditAction,
    note: str | None = None,
) -> CameraConfigVersion:
    # The row lock makes concurrent approvals of one version see each other's result.
    camera = _camera(principal, camera_id, lock=True)
    version = _version(principal, camera, version_id)
    before = version.status
    errors: list[dict[str, str]] = []
    with _guard(principal, camera, name):
        if name == "validate":
            errors = ctl.validate_version(version)
        elif name == "submit":
            ctl.submit_version(version, principal.user_id)
        elif name == "approve":
            ctl.approve_version(version, principal.user_id, note)
        else:
            ctl.reject_version(version, principal.user_id, note)
        principal.db.commit()
    if before != version.status or name == "validate":
        principal.audit(
            action,
            resource_type="cameras",
            resource_id=camera.id,
            details={
                "camera": camera.slug,
                "version_id": str(version.id),
                "config_revision": version.revision,
                "fingerprint": version.fingerprint,
                "before": before,
                "after": version.status,
                "error_count": len(errors),
                "note": note,
            },
        )
    return version


@router.post("/cameras/{camera_id}/versions/{version_id}/validate", response_model=s.VersionOut)
def validate_version(
    camera_id: uuid.UUID, version_id: uuid.UUID, principal: Principal = MANAGE
) -> CameraConfigVersion:
    return _version_action(
        principal, camera_id, version_id, "validate", AuditAction.camera_config_validated
    )


@router.post("/cameras/{camera_id}/versions/{version_id}/submit", response_model=s.VersionOut)
def submit_version(
    camera_id: uuid.UUID, version_id: uuid.UUID, body: s.SubmitIn, principal: Principal = MANAGE
) -> CameraConfigVersion:
    return _version_action(
        principal,
        camera_id,
        version_id,
        "submit",
        AuditAction.camera_config_submitted,
        body.reason,
    )


@router.post("/cameras/{camera_id}/versions/{version_id}/approve", response_model=s.VersionOut)
def approve_version(
    camera_id: uuid.UUID, version_id: uuid.UUID, body: s.DecisionIn, principal: Principal = MANAGE
) -> CameraConfigVersion:
    return _version_action(
        principal, camera_id, version_id, "approve", AuditAction.camera_config_approved, body.note
    )


@router.post("/cameras/{camera_id}/versions/{version_id}/reject", response_model=s.VersionOut)
def reject_version(
    camera_id: uuid.UUID, version_id: uuid.UUID, body: s.DecisionIn, principal: Principal = MANAGE
) -> CameraConfigVersion:
    return _version_action(
        principal, camera_id, version_id, "reject", AuditAction.camera_config_rejected, body.note
    )


def _activate(
    principal: Principal, camera_id: uuid.UUID, body: s.ActivateIn, rollback: bool
) -> s.ActivationOut:
    camera = _camera(principal, camera_id, lock=True)
    version = _version(principal, camera, body.version_id)
    with _guard(principal, camera, "rollback" if rollback else "activate"):
        result = ctl.activate(
            principal.db,
            camera,
            version,
            actor_id=principal.user_id,
            expected_revision=body.expected_revision,
            reason=body.reason,
            rollback=rollback,
        )
        if result.changed:
            ctl.add_event(
                principal.db,
                camera,
                "control",
                revision=version.revision,
                reason_code="rollback" if rollback else "activate",
            )
        principal.db.commit()
    if result.changed:
        _audit_camera(
            principal,
            (
                AuditAction.camera_config_rolled_back
                if rollback
                else AuditAction.camera_config_activated
            ),
            camera,
            version_id=str(version.id),
            before_fingerprint=result.previous.fingerprint if result.previous else None,
            before_config_revision=result.previous.revision if result.previous else None,
            after_fingerprint=version.fingerprint,
            after_config_revision=version.revision,
            reason=body.reason,
        )
    return s.ActivationOut(
        changed=result.changed,
        camera=_summary(principal, camera),
        version=s.VersionSummary.model_validate(version),
        previous_version_id=result.previous.id if result.previous else None,
    )


@router.post("/cameras/{camera_id}/activate", response_model=s.ActivationOut)
def activate(
    camera_id: uuid.UUID, body: s.ActivateIn, principal: Principal = MANAGE
) -> s.ActivationOut:
    return _activate(principal, camera_id, body, rollback=False)


@router.post("/cameras/{camera_id}/rollback", response_model=s.ActivationOut)
def rollback(
    camera_id: uuid.UUID, body: s.ActivateIn, principal: Principal = MANAGE
) -> s.ActivationOut:
    """Re-activate a previously active (SUPERSEDED) version; no row's config is modified."""
    return _activate(principal, camera_id, body, rollback=True)
