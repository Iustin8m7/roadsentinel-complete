"""Camera control plane: source registration, processing grants, config version lifecycle,
activation (compare-and-swap), lifecycle actions, worker handshake (lease, ack, heartbeat) and
truthful status derivation.

Design notes (see docs/camera-config-contract.md):

* ``cameras.revision`` is the optimistic-concurrency token. Every camera mutation takes a row
  lock (``SELECT ... FOR UPDATE``), compares ``expected_revision`` and increments it, so two
  admins racing cannot both win.
* Four-eyes: every config version needs approval by a tenant admin who neither created nor
  submitted it; re-enabling a DISABLED camera needs a request and a confirmation by two
  different admins. The database CHECK ``ck_camera_config_versions_four_eyes`` backs the first.
* Cameras in lifecycle ``legacy`` (registered before the control plane) keep the old ingest
  behaviour; every other camera only accepts evidence while it is runnable.
* No function here opens a network connection: the source URL is only parsed and stored.
"""

from __future__ import annotations

import hashlib
import posixpath
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.crypto import TenantKeyring, encrypt_field
from app.core.redaction import redact_text
from app.models import (
    Camera,
    CameraConfigVersion,
    CameraHealthEvent,
    CameraSourceGrant,
    CameraWorkerStatus,
)
from app.services import camera_config as cc

LIFECYCLE_STATES = ("legacy", "discovered", "onboarding", "approved", "disabled")
SOURCE_KINDS = ("recorded_replay", "owned_optical_live", "authorized_network_live")
LIVE_KINDS = ("owned_optical_live", "authorized_network_live")
SOURCE_SCHEMES: dict[str, tuple[str, ...]] = {
    "recorded_replay": ("replay",),
    "owned_optical_live": ("rtsp", "rtsps", "https", "device"),
    "authorized_network_live": ("rtsp", "rtsps", "https"),
}
SOURCE_URL_FIELD = "cameras.source_url"
REPLAY_REF = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9._/-]{0,199}$")
DEVICE_REF = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
HOST = re.compile(r"^[A-Za-z0-9.-]{1,253}$|^\[[0-9A-Fa-f:.]{2,45}\]$")

# Heartbeats arrive every ~30 s: three missed ones make a worker stale, 10 minutes offline.
HEARTBEAT_STALE_AFTER = timedelta(seconds=90)
HEARTBEAT_OFFLINE_AFTER = timedelta(minutes=10)
LEASE_TTL = timedelta(seconds=90)
HEALTH_HISTORY_CAP = 200  # newest events kept per camera

HEALTH_STATES = (
    "starting",
    "healthy",
    "reconnecting",
    "source_failed",
    "decoder_failed",
    "model_unavailable",
    "config_rejected",
    "auth_failed",
    "permission_blocked",
    "stopped",
    "frozen_image",
)
UNSUPPORTED_ACTIONS = {
    "restart": "Repornirea de la distanță nu este implementată: workerul nu are un supervizor "
    "controlat de server. Opriți și reporniți procesul pe mașina care îl rulează.",
}


class ControlError(Exception):
    """A refused control-plane operation. ``code`` is stable; ``extra`` is safe to return."""

    def __init__(self, status: int, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.extra = status, code, message, extra

    def detail(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, **self.extra}


def _now() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------- source URL


_URL_IN_TEXT = re.compile(r"\b[A-Za-z][A-Za-z0-9+.-]{1,15}://\S+")


def sanitize_message(text: str | None, limit: int = 300) -> str | None:
    """Worker-supplied text without URLs (they may carry credentials) or secret-looking pairs."""
    if not text:
        return None
    cleaned = redact_text(_URL_IN_TEXT.sub("[url]", text))
    return "".join(ch if ch.isprintable() else " " for ch in cleaned)[:limit]


@dataclass(frozen=True)
class ParsedSource:
    display: str
    has_credentials: bool


def parse_source(kind: str, url: str) -> ParsedSource:
    """Check a source reference against the allow-list. Error messages never echo the URL.

    The server never fetches it (no SSRF primitive); a replay reference names a recording the
    worker already has, never an arbitrary server path."""
    if kind not in SOURCE_KINDS:
        raise ControlError(422, "unsupported_source_kind", "Unsupported source kind")
    if not url or len(url) > 2048 or any(ch.isspace() or not ch.isprintable() for ch in url):
        raise ControlError(422, "invalid_source_url", "Source URL is malformed")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise ControlError(422, "invalid_source_url", "Source URL is malformed") from None
    scheme = parts.scheme.lower()
    if scheme not in SOURCE_SCHEMES[kind]:
        allowed = ", ".join(SOURCE_SCHEMES[kind])
        raise ControlError(
            422, "unsupported_scheme", f"Scheme not allowed for {kind} (allowed: {allowed})"
        )
    if scheme == "replay":
        ref = (parts.netloc + parts.path).lstrip("/") if parts.netloc else parts.path
        if (
            parts.query
            or parts.fragment
            or "@" in url
            or not REPLAY_REF.match(ref)
            or ".." in ref.split("/")
            or "//" in ref
        ):
            raise ControlError(
                422, "invalid_replay_reference", "Replay reference must be a relative name"
            )
        return ParsedSource(f"replay://{ref}", False)
    if scheme == "device":
        if not DEVICE_REF.match(parts.netloc) or parts.path not in ("", "/") or parts.query:
            raise ControlError(422, "invalid_device_reference", "Device reference is malformed")
        return ParsedSource(f"device://{parts.netloc}", False)
    host = parts.hostname or ""
    if not host or not HOST.match(host if ":" not in host else f"[{host}]"):
        raise ControlError(422, "invalid_source_url", "Source URL needs a valid host")
    has_credentials = bool(parts.username or parts.password or parts.query or parts.fragment)
    shown_host = f"[{host}]" if ":" in host else host
    display = f"{scheme}://{shown_host}" + (f":{port}" if port else "")
    return ParsedSource(display, has_credentials)


# --------------------------------------------------------------------------- source identity

# Ports dropped from the identity when they are the scheme's default.
DEFAULT_PORTS = {"rtsp": 554, "rtsps": 322, "https": 443}


def source_identity(url: str) -> str:
    """Normalized, credential-free identity of a registered source: lower-case scheme and host,
    non-default port, path; user info, query and fragment dropped. Same algorithm as the
    worker's ``roadsentinel.remote_config.source_identity`` (shared fixture
    ``tests/fixtures/camera_config/source_identity.json``). Never logged or returned."""
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme == "replay":
        ref = (parts.netloc + parts.path) if parts.netloc else parts.path
        return "replay://" + posixpath.normpath(ref.lstrip("/"))
    if scheme == "device":
        return f"device://{parts.netloc}"
    host = (parts.hostname or "").lower()
    if ":" in host:
        host = f"[{host}]"
    port = parts.port
    shown_port = f":{port}" if port and port != DEFAULT_PORTS.get(scheme) else ""
    return f"{scheme}://{host}{shown_port}{parts.path or '/'}"


def source_fingerprint(url: str) -> str:
    """SHA-256 of ``source_identity``: lets the backend compare what a worker reports it opened
    with what was registered. It detects misconfiguration, not a lying worker."""
    return hashlib.sha256(source_identity(url).encode()).hexdigest()


# --------------------------------------------------------------------------- eligibility


@dataclass(frozen=True)
class Unmet:
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


def _grant_unmet(
    grant: CameraSourceGrant, camera: Camera, config: dict[str, Any] | None, now: datetime
) -> list[Unmet]:
    out: list[Unmet] = []
    if grant.status != "active":
        out.append(Unmet("grant_revoked", "The processing authorization was revoked"))
    if grant.valid_from > now:
        out.append(Unmet("grant_not_yet_valid", "The processing authorization is not valid yet"))
    if grant.valid_until <= now:
        out.append(Unmet("grant_expired", "The processing authorization has expired"))
    if camera.source_kind and grant.capture_method != camera.source_kind:
        out.append(
            Unmet(
                "grant_capture_method_mismatch",
                "The authorization covers a different capture method than the source",
            )
        )
    if config:
        fps = (config.get("acquisition") or {}).get("target_fps")
        if isinstance(fps, int | float) and fps > grant.max_analysis_fps:
            out.append(
                Unmet("grant_fps_exceeded", "Configured frame rate exceeds the authorized rate")
            )
        height = (config.get("reference_frame") or {}).get("height")
        if isinstance(height, int | float) and height > grant.max_frame_height:
            out.append(
                Unmet(
                    "grant_resolution_exceeded",
                    "Reference frame is larger than the authorized quality",
                )
            )
    return out


def evaluate_eligibility(
    camera: Camera,
    grants: list[CameraSourceGrant],
    version: CameraConfigVersion | None,
    now: datetime | None = None,
) -> list[Unmet]:
    """ALL unmet requirements for processing ``camera`` with ``version`` (dry-run, no network).

    Empty list = eligible. ``version`` None means the camera's active configuration."""
    now = now or _now()
    unmet: list[Unmet] = []
    if camera.lifecycle_state == "legacy":
        unmet.append(Unmet("camera_not_managed", "Camera is not under the control plane"))
    elif camera.lifecycle_state == "discovered":
        unmet.append(Unmet("camera_not_onboarded", "A discovered camera must be registered first"))
    if not camera.source_kind or not camera.source_display:
        unmet.append(Unmet("source_missing", "No source is registered for this camera"))
    config = version.config if version is not None else None
    if version is None:
        unmet.append(Unmet("config_missing", "No configuration version is active"))
    else:
        if version.camera_id != camera.id:
            unmet.append(Unmet("config_foreign", "Version belongs to another camera"))
        if version.status not in ("approved", "active", "superseded"):
            unmet.append(Unmet("config_not_approved", "Configuration version is not approved"))
        if cc.validate(version.config):
            unmet.append(Unmet("config_invalid", "Configuration version does not validate"))
    candidates = [g for g in grants if g.camera_id == camera.id]
    if not candidates:
        unmet.append(Unmet("grant_missing", "No processing authorization is recorded"))
    else:
        options = [_grant_unmet(g, camera, config, now) for g in candidates]
        best = min(options, key=len)
        unmet.extend(best)
    return unmet


def grant_allows_recordings(camera: Camera, grants: list[CameraSourceGrant], now: datetime) -> bool:
    return any(
        g.media_scope == "events_and_recordings" and not _grant_unmet(g, camera, None, now)
        for g in grants
    )


def grant_allows_export(camera: Camera, grants: list[CameraSourceGrant], now: datetime) -> bool:
    """For the evidence-export workstream: legacy cameras are not covered by grants."""
    return any(g.export_allowed and not _grant_unmet(g, camera, None, now) for g in grants)


# --------------------------------------------------------------------------- loading helpers


def grants_for(db: Session, camera_id: uuid.UUID) -> list[CameraSourceGrant]:
    return list(
        db.scalars(
            select(CameraSourceGrant)
            .where(CameraSourceGrant.camera_id == camera_id)
            .order_by(CameraSourceGrant.created_at)
        )
    )


def active_version(db: Session, camera: Camera) -> CameraConfigVersion | None:
    return db.get(CameraConfigVersion, camera.active_config_id) if camera.active_config_id else None


def lock_camera(db: Session, camera_id: uuid.UUID) -> Camera | None:
    return db.scalars(
        select(Camera)
        .where(Camera.id == camera_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()


def runnable(
    db: Session, camera: Camera, now: datetime | None = None
) -> tuple[bool, str | None, list[Unmet]]:
    """May a worker process this camera right now? (True for legacy cameras: unchanged.)"""
    if not camera.is_active:
        return False, "camera_inactive", []
    if camera.lifecycle_state == "legacy":
        return True, None, []
    if camera.lifecycle_state == "disabled":
        return False, "disabled", []
    if camera.lifecycle_state != "approved" or camera.active_config_id is None:
        return False, "not_activated", []
    if not camera.desired_enabled:
        return False, "paused", []
    unmet = evaluate_eligibility(camera, grants_for(db, camera.id), active_version(db, camera), now)
    if unmet:
        return False, "not_authorized", unmet
    if source_attestation(camera, worker_status(db, camera.id), now or _now()) == "mismatch":
        return False, "source_mismatch", []
    return True, None, []


def source_attestation(camera: Camera, row: CameraWorkerStatus | None, now: datetime) -> str:
    """Does the CURRENT lease holder report the registered source? Only a valid lease counts, so
    a stopped or crashed worker's old report never blocks the next one."""
    if (
        row is None
        or not row.source_fingerprint
        or not (row.lease_expires_at and row.lease_expires_at > now)
    ):
        return "unreported"
    if not camera.source_fingerprint:
        return "unknown"
    return "match" if row.source_fingerprint == camera.source_fingerprint else "mismatch"


def _check_revision(camera: Camera, expected: int) -> None:
    if camera.revision != expected:
        raise ControlError(
            409,
            "revision_conflict",
            "The camera changed since it was loaded; reload and retry",
            current_revision=camera.revision,
        )


def add_event(
    db: Session,
    camera: Camera,
    kind: str,
    *,
    at: datetime | None = None,
    worker_epoch: str | None = None,
    health: str | None = None,
    revision: int | None = None,
    reason_code: str | None = None,
    message: str | None = None,
) -> None:
    """Append a history event and keep only the newest HEALTH_HISTORY_CAP for the camera."""
    db.add(
        CameraHealthEvent(
            tenant_id=camera.tenant_id,
            camera_id=camera.id,
            at=at or _now(),
            kind=kind,
            worker_epoch=worker_epoch,
            health=health,
            revision=revision,
            reason_code=reason_code,
            message=sanitize_message(message),
        )
    )
    db.flush()
    keep = (
        select(CameraHealthEvent.id)
        .where(CameraHealthEvent.camera_id == camera.id)
        .order_by(CameraHealthEvent.at.desc(), CameraHealthEvent.id.desc())
        .limit(HEALTH_HISTORY_CAP)
    )
    db.execute(
        delete(CameraHealthEvent).where(
            CameraHealthEvent.camera_id == camera.id, CameraHealthEvent.id.not_in(keep)
        )
    )


# --------------------------------------------------------------------------- camera actions


def set_source(
    db: Session,
    keyring: TenantKeyring,
    camera: Camera,
    *,
    kind: str,
    url: str,
    expected_revision: int,
) -> dict[str, Any]:
    """Register or replace the source. Returns non-secret before/after for the audit log."""
    parsed = parse_source(kind, url)
    _check_revision(camera, expected_revision)
    before = {"kind": camera.source_kind, "display": camera.source_display}
    camera.source_kind = kind
    camera.source_display = parsed.display
    camera.source_has_credentials = parsed.has_credentials
    camera.source_url_enc = encrypt_field(keyring, SOURCE_URL_FIELD, url)
    camera.source_fingerprint = source_fingerprint(url)
    # A request to re-enable was about the previous source: it cannot approve this one.
    camera.enable_requested_by = camera.enable_requested_at = None
    if camera.lifecycle_state == "approved":
        # A new source must be reviewed again: re-enabling is four-eyes.
        camera.lifecycle_state = "disabled"
        camera.desired_enabled = False
        camera.disabled_reason = "source_changed"
    camera.revision += 1
    db.flush()
    return {
        "before": before,
        "after": {"kind": kind, "display": parsed.display},
        "has_credentials": parsed.has_credentials,
    }


def transition_lifecycle(camera: Camera, to: str, expected_revision: int) -> str:
    allowed = {("legacy", "onboarding"), ("discovered", "onboarding")}
    if (camera.lifecycle_state, to) not in allowed:
        raise ControlError(
            409,
            "invalid_transition",
            f"Cannot move a camera from {camera.lifecycle_state} to {to} with this action",
        )
    seen = camera.last_seen_at
    if camera.lifecycle_state == "legacy" and seen and _now() - seen <= HEARTBEAT_OFFLINE_AFTER:
        # Adopted cameras have their evidence refused until a config is activated.
        raise ControlError(
            409, "worker_active", "Stop this camera's worker before placing it under control"
        )
    _check_revision(camera, expected_revision)
    before = camera.lifecycle_state
    camera.lifecycle_state = to
    camera.revision += 1
    return before


def pause(camera: Camera, expected_revision: int) -> None:
    if camera.lifecycle_state != "approved" or not camera.desired_enabled:
        if camera.lifecycle_state == "approved":
            return  # already paused: idempotent
        raise ControlError(409, "invalid_transition", "Only a running camera can be paused")
    _check_revision(camera, expected_revision)
    camera.desired_enabled = False
    camera.revision += 1


def resume(db: Session, camera: Camera, expected_revision: int) -> None:
    if camera.lifecycle_state != "approved":
        raise ControlError(409, "invalid_transition", "Only a paused, approved camera can resume")
    if camera.desired_enabled:
        return
    _check_revision(camera, expected_revision)
    unmet = evaluate_eligibility(camera, grants_for(db, camera.id), active_version(db, camera))
    if unmet:
        raise ControlError(409, "not_eligible", "Requirements are not met", unmet=_d(unmet))
    camera.desired_enabled = True
    camera.revision += 1


def disable(camera: Camera, expected_revision: int, reason: str) -> None:
    if camera.lifecycle_state == "disabled":
        return
    if camera.lifecycle_state == "legacy":
        # Nothing could re-enable it: legacy cameras are outside the control plane until adopted.
        raise ControlError(409, "camera_not_managed", "Camera is not under the control plane")
    _check_revision(camera, expected_revision)
    camera.lifecycle_state = "disabled"
    camera.desired_enabled = False
    camera.disabled_reason = reason[:300]
    camera.enable_requested_by = camera.enable_requested_at = None
    camera.revision += 1


def request_enable(camera: Camera, actor_id: uuid.UUID, expected_revision: int) -> None:
    if camera.lifecycle_state != "disabled":
        raise ControlError(409, "invalid_transition", "Camera is not disabled")
    _check_revision(camera, expected_revision)
    camera.enable_requested_by, camera.enable_requested_at = actor_id, _now()
    camera.revision += 1


def confirm_enable(
    db: Session, camera: Camera, actor_id: uuid.UUID, expected_revision: int
) -> None:
    if camera.lifecycle_state != "disabled":
        raise ControlError(409, "invalid_transition", "Camera is not disabled")
    if camera.enable_requested_by is None:
        raise ControlError(409, "enable_not_requested", "Re-enabling must be requested first")
    if camera.enable_requested_by == actor_id:
        raise ControlError(
            403, "four_eyes_required", "A second administrator must confirm re-enabling"
        )
    _check_revision(camera, expected_revision)
    version = active_version(db, camera)
    if version is not None:
        unmet = evaluate_eligibility(camera, grants_for(db, camera.id), version)
        if unmet:
            raise ControlError(409, "not_eligible", "Requirements are not met", unmet=_d(unmet))
        camera.lifecycle_state, camera.desired_enabled = "approved", True
    else:
        camera.lifecycle_state, camera.desired_enabled = "onboarding", False
    camera.disabled_reason = None
    camera.enable_requested_by = camera.enable_requested_at = None
    camera.revision += 1


def _d(unmet: list[Unmet]) -> list[dict[str, str]]:
    return [u.as_dict() for u in unmet]


# --------------------------------------------------------------------------- versions


def create_version(
    db: Session, camera: Camera, config: dict[str, Any], actor_id: uuid.UUID, reason: str
) -> CameraConfigVersion:
    """New DRAFT (camera row must be locked by the caller so revisions stay gap-free)."""
    if camera.lifecycle_state in ("legacy", "discovered"):
        raise ControlError(
            409, "camera_not_onboarded", "Register the camera (onboarding) before configuring it"
        )
    canonical = cc.canonicalize(config)
    last = db.scalar(
        select(func.max(CameraConfigVersion.revision)).where(
            CameraConfigVersion.camera_id == camera.id
        )
    )
    version = CameraConfigVersion(
        tenant_id=camera.tenant_id,
        camera_id=camera.id,
        revision=(last or 0) + 1,
        schema_version=(
            canonical.get("schema_version")
            if isinstance(canonical.get("schema_version"), int)
            else 0
        ),
        config=canonical,
        fingerprint=cc.fingerprint(canonical),
        status="draft",
        validation_errors=[e.as_dict() for e in cc.validate(canonical)],
        reason=reason,
        created_by=actor_id,
    )
    db.add(version)
    db.flush()
    return version


def validate_version(version: CameraConfigVersion) -> list[dict[str, str]]:
    errors = [e.as_dict() for e in cc.validate(version.config)]
    if version.status == "draft":
        version.validation_errors = errors
        if not errors:
            version.status, version.validated_at = "validated", _now()
    return errors


def submit_version(version: CameraConfigVersion, actor_id: uuid.UUID) -> None:
    if version.status == "awaiting_approval":
        return
    if version.status != "validated":
        raise ControlError(409, "invalid_transition", "Only a validated version can be submitted")
    version.status, version.submitted_by, version.submitted_at = (
        "awaiting_approval",
        actor_id,
        _now(),
    )


def _four_eyes(version: CameraConfigVersion, actor_id: uuid.UUID) -> None:
    if actor_id in (version.created_by, version.submitted_by):
        raise ControlError(
            403,
            "four_eyes_required",
            "The approver must be a different administrator than the author and submitter",
        )


def approve_version(version: CameraConfigVersion, actor_id: uuid.UUID, note: str | None) -> None:
    if version.status != "awaiting_approval":
        raise ControlError(409, "invalid_transition", "Version is not awaiting approval")
    _four_eyes(version, actor_id)
    if cc.validate(version.config):
        raise ControlError(409, "config_invalid", "Version no longer validates")
    version.status, version.decided_by, version.decided_at = "approved", actor_id, _now()
    version.decision_note = note


def reject_version(version: CameraConfigVersion, actor_id: uuid.UUID, note: str | None) -> None:
    if version.status not in ("draft", "validated", "awaiting_approval"):
        raise ControlError(409, "invalid_transition", "Version can no longer be rejected")
    _four_eyes(version, actor_id)
    version.status, version.decided_by, version.decided_at = "rejected", actor_id, _now()
    version.decision_note = note


@dataclass
class Activation:
    changed: bool
    previous: CameraConfigVersion | None
    version: CameraConfigVersion


def activate(
    db: Session,
    camera: Camera,
    version: CameraConfigVersion,
    *,
    actor_id: uuid.UUID,
    expected_revision: int,
    reason: str,
    rollback: bool,
) -> Activation:
    """Make ``version`` the camera's desired config. The camera row must be locked.

    Idempotent: re-activating the already-active version returns ``changed=False`` even with
    the (now stale) revision of the first call."""
    if version.camera_id != camera.id:
        raise ControlError(404, "not_found", "Not found")
    if camera.active_config_id == version.id and version.status == "active":
        return Activation(False, None, version)
    _check_revision(camera, expected_revision)
    if rollback and version.status != "superseded":
        raise ControlError(
            409, "invalid_transition", "Rollback targets a previously active version"
        )
    if not rollback and version.status != "approved":
        raise ControlError(409, "version_not_approved", "Only an approved version can be activated")
    if camera.lifecycle_state in ("legacy", "discovered"):
        raise ControlError(409, "camera_not_onboarded", "Register the camera first")
    unmet = evaluate_eligibility(camera, grants_for(db, camera.id), version)
    if unmet:
        raise ControlError(409, "not_eligible", "Requirements are not met", unmet=_d(unmet))
    now = _now()
    previous = active_version(db, camera)
    if previous is not None:
        previous.status, previous.superseded_at = "superseded", now
        db.flush()  # one ACTIVE row at a time (trigger checks each transition)
    version.status, version.activated_by, version.activated_at = "active", actor_id, now
    version.activation_reason = reason
    camera.active_config_id = version.id
    if camera.lifecycle_state != "disabled":
        camera.lifecycle_state, camera.desired_enabled = "approved", True
    camera.revision += 1
    db.flush()
    return Activation(True, previous, version)


# --------------------------------------------------------------------------- worker side


def desired_for_worker(db: Session, camera: Camera) -> dict[str, Any]:
    """What a worker should run. Never a draft: only the ACTIVE version, and only while the
    camera is runnable (enabled, approved, authorized)."""
    ok, reason, unmet = runnable(db, camera)
    out: dict[str, Any] = {
        "camera_id": camera.slug,
        "managed": camera.lifecycle_state != "legacy",
        "run": ok,
        "reason": reason,
        "unmet": [u.code for u in unmet],
        "camera_revision": camera.revision,
        "source_kind": camera.source_kind,
        "source_fingerprint": camera.source_fingerprint,
        "revision": None,
        "fingerprint": None,
        "config": None,
    }
    version = active_version(db, camera)
    if ok and version is not None:
        out.update(
            revision=version.revision, fingerprint=version.fingerprint, config=version.config
        )
    return out


def _status_row(db: Session, camera: Camera) -> CameraWorkerStatus:
    db.execute(
        pg_insert(CameraWorkerStatus)
        .values(
            id=uuid.uuid4(),
            tenant_id=camera.tenant_id,
            camera_id=camera.id,
            seq=0,
            updated_at=_now(),
        )
        .on_conflict_do_nothing(index_elements=["camera_id"])
    )
    row = db.scalars(
        select(CameraWorkerStatus)
        .where(CameraWorkerStatus.camera_id == camera.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    return row


def worker_status(db: Session, camera_id: uuid.UUID) -> CameraWorkerStatus | None:
    return db.scalars(
        select(CameraWorkerStatus).where(CameraWorkerStatus.camera_id == camera_id)
    ).first()


@dataclass
class HeartbeatResult:
    lease: str  # holder | standby
    directive: str  # run | stop
    reason: str | None
    desired_revision: int | None
    desired_fingerprint: str | None
    camera_revision: int
    unmet: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "lease": self.lease,
            "directive": self.directive,
            "reason": self.reason,
            "desired_revision": self.desired_revision,
            "desired_fingerprint": self.desired_fingerprint,
            "camera_revision": self.camera_revision,
            "unmet": self.unmet,
        }


def _directive(db: Session, camera: Camera, lease: str, reason: str | None) -> HeartbeatResult:
    version = active_version(db, camera)
    ok, why, unmet = runnable(db, camera)
    run = ok and lease == "holder"
    return HeartbeatResult(
        lease=lease,
        directive="run" if run else "stop",
        reason=reason or why,
        desired_revision=version.revision if version else None,
        desired_fingerprint=version.fingerprint if version else None,
        camera_revision=camera.revision,
        unmet=[u.code for u in unmet],
    )


TELEMETRY_FIELDS = (
    "health",
    "source_fps",
    "processing_fps",
    "last_frame_at",
    "dropped_frames",
    "queue_depth",
    "retries",
    "model_id",
    "frame_width",
    "frame_height",
    "inference_p50_ms",
    "inference_p95_ms",
    "rss_mb",
    "frozen_signal",
    "frozen_confidence",
    "unchanged_s",
)


def _sync_applied(
    db: Session,
    camera: Camera,
    row: CameraWorkerStatus,
    reported: int | None,
    new_epoch: bool,
    now: datetime,
) -> None:
    """The applied revision is what the current lease holder says it runs: a new worker that
    reports nothing has applied nothing, and a revision never delivered is ignored."""
    if reported is None:
        if new_epoch:
            row.applied_revision = row.applied_fingerprint = row.applied_at = None
        return
    if reported == row.applied_revision:
        return
    version = db.scalars(
        select(CameraConfigVersion).where(
            CameraConfigVersion.camera_id == camera.id, CameraConfigVersion.revision == reported
        )
    ).first()
    if version is not None and version.status in ("active", "superseded"):
        row.applied_revision, row.applied_fingerprint = version.revision, version.fingerprint
        row.applied_at = now


def record_heartbeat(
    db: Session, camera: Camera, hb: dict[str, Any], now: datetime | None = None
) -> HeartbeatResult:
    """Store a worker heartbeat under the per-camera processing lease.

    Only one worker epoch holds the lease (renewed by each heartbeat, LEASE_TTL). Another
    epoch heartbeating while it is valid is recorded as a conflict and told to stop. Older or
    repeated sequence numbers of the holder never overwrite newer telemetry."""
    now = now or _now()
    row = _status_row(db, camera)
    epoch: str = hb["worker_epoch"]
    if (
        row.lease_epoch
        and row.lease_epoch != epoch
        and row.lease_expires_at
        and row.lease_expires_at > now
    ):
        if row.conflict_epoch != epoch:
            add_event(db, camera, "lease_conflict", at=now, worker_epoch=epoch)
        row.conflict_epoch, row.conflict_at = epoch, now
        db.flush()
        return _directive(db, camera, "standby", "duplicate_worker")
    new_epoch = row.lease_epoch != epoch
    if new_epoch:
        add_event(db, camera, "lease_acquired", at=now, worker_epoch=epoch)
        row.lease_epoch, row.seq = epoch, -1
    elif hb["seq"] <= row.seq:
        db.flush()
        return _directive(db, camera, "holder", "stale_sequence")
    previous_health = row.health
    row.seq = hb["seq"]
    row.last_heartbeat_at = now
    row.updated_at = now
    for key in TELEMETRY_FIELDS:
        if key in hb and hb[key] is not None:
            setattr(row, key, hb[key])
    _sync_applied(db, camera, row, hb.get("applied_revision"), new_epoch, now)
    row.last_error_code = hb.get("error_code")
    row.last_error = sanitize_message(hb.get("error_message"))
    reported = hb.get("source_fingerprint")
    if (
        reported
        and camera.lifecycle_state != "legacy"
        and camera.source_fingerprint
        and reported != camera.source_fingerprint
        and (new_epoch or reported != row.source_fingerprint)
    ):
        add_event(db, camera, "source_mismatch", at=now, worker_epoch=epoch)
    row.source_fingerprint = reported  # what this lease holder opened (None: not reported)
    if hb.get("health") == "stopped":
        row.lease_expires_at = now  # graceful stop releases the lease at once
    else:
        row.lease_expires_at = now + LEASE_TTL
    if hb.get("health") and hb["health"] != previous_health:
        add_event(
            db,
            camera,
            "health",
            at=now,
            worker_epoch=epoch,
            health=hb["health"],
            revision=hb.get("applied_revision"),
            reason_code=hb.get("error_code"),
            message=hb.get("error_message"),
        )
    camera.last_seen_at = now
    db.flush()
    return _directive(db, camera, "holder", None)


def record_ack(
    db: Session, camera: Camera, ack: dict[str, Any], now: datetime | None = None
) -> CameraWorkerStatus:
    now = now or _now()
    version = db.scalars(
        select(CameraConfigVersion).where(
            CameraConfigVersion.camera_id == camera.id,
            CameraConfigVersion.revision == ack["revision"],
        )
    ).first()
    if version is None or version.fingerprint != ack["fingerprint"]:
        raise ControlError(422, "unknown_revision", "No such revision/fingerprint for this camera")
    if version.status not in ("active", "superseded"):
        raise ControlError(422, "unknown_revision", "Revision was never delivered to workers")
    row = _status_row(db, camera)
    if (
        row.lease_epoch
        and row.lease_epoch != ack["worker_epoch"]
        and row.lease_expires_at
        and row.lease_expires_at > now
    ):
        raise ControlError(409, "not_lease_holder", "Another worker holds this camera's lease")
    if camera.lifecycle_state != "legacy" and (
        row.lease_epoch != ack["worker_epoch"] or not row.lease_expires_at
        or row.lease_expires_at <= now or version.status != "active"
    ):
        raise ControlError(409, "not_lease_holder", "Current lease and active revision required")
    if ack["status"] == "accepted":
        row.applied_revision, row.applied_fingerprint, row.applied_at = (
            version.revision,
            version.fingerprint,
            now,
        )
    row.last_ack_status, row.last_ack_revision = ack["status"], version.revision
    row.last_ack_reason, row.last_ack_at = ack.get("reason_code"), now
    row.updated_at = now
    add_event(
        db,
        camera,
        "ack",
        at=now,
        worker_epoch=ack["worker_epoch"],
        revision=version.revision,
        reason_code=f"{ack['status']}:{ack.get('reason_code') or 'ok'}"[:64],
        message=ack.get("message"),
    )
    db.flush()
    return row


# --------------------------------------------------------------------------- status


PROBLEM_HEALTH = {
    "reconnecting",
    "source_failed",
    "decoder_failed",
    "model_unavailable",
    "config_rejected",
    "auth_failed",
    "permission_blocked",
    "starting",
    "stopped",
    "frozen_image",
}


def derive_status(
    db: Session, camera: Camera, row: CameraWorkerStatus | None, now: datetime | None = None
) -> dict[str, Any]:
    """Server-side, truthful runtime state. A replay is never reported as LIVE, and a worker
    whose heartbeat is older than HEARTBEAT_STALE_AFTER is never reported as running."""
    now = now or _now()
    version = active_version(db, camera)
    last = row.last_heartbeat_at if row else None
    if last is None and camera.lifecycle_state == "legacy":
        last = camera.last_seen_at  # legacy workers send empty heartbeats: no status row
    age = (now - last).total_seconds() if last else None
    if last is None:
        freshness = "never"
    elif now - last > HEARTBEAT_OFFLINE_AFTER:
        freshness = "offline"
    elif now - last > HEARTBEAT_STALE_AFTER:
        freshness = "stale"
    else:
        freshness = "fresh"
    ok, why, unmet = runnable(db, camera, now)
    if camera.lifecycle_state == "disabled":
        state = "disabled"
    elif camera.lifecycle_state == "discovered":
        state = "not_onboarded"
    elif camera.lifecycle_state == "onboarding":
        state = "onboarding"
    elif camera.lifecycle_state == "approved" and not camera.desired_enabled:
        state = "paused"
    elif why == "not_authorized":
        state = "permission_blocked"
    elif why == "source_mismatch":
        state = "source_mismatch"
    elif freshness == "never":
        state = "never_seen"
    elif freshness in ("stale", "offline"):
        state = freshness
    elif row and row.health in PROBLEM_HEALTH:
        state = row.health or "unknown"
    elif camera.source_kind in LIVE_KINDS:
        state = "live"
    elif camera.source_kind == "recorded_replay":
        state = "replay"
    else:
        state = "processing"  # legacy camera with an undeclared source: never claimed LIVE
    mismatch = None
    if version and row and row.frame_width and row.frame_height:
        ref = version.config.get("reference_frame") or {}
        mismatch = (row.frame_width, row.frame_height) != (ref.get("width"), ref.get("height"))
    conflict = bool(
        row and row.conflict_at and now - row.conflict_at <= LEASE_TTL and row.conflict_epoch
    )
    return {
        "state": state,
        "is_live": state == "live",
        "freshness": freshness,
        "heartbeat_age_s": round(age, 1) if age is not None else None,
        "stale_after_s": HEARTBEAT_STALE_AFTER.total_seconds(),
        "offline_after_s": HEARTBEAT_OFFLINE_AFTER.total_seconds(),
        "runnable": ok,
        "blocked_reason": why,
        "unmet": _d(unmet),
        "desired_revision": version.revision if version else None,
        "desired_fingerprint": version.fingerprint if version else None,
        "applied_revision": row.applied_revision if row else None,
        "applied_fingerprint": row.applied_fingerprint if row else None,
        "revision_in_sync": bool(
            version and row and row.applied_fingerprint == version.fingerprint
        ),
        "reference_frame_mismatch": mismatch,
        "duplicate_worker": conflict,
        "source_attestation": source_attestation(camera, row, now),
        "server_time": now,
    }
