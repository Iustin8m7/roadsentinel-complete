"""Controlled evidence-package export: request -> four-eyes approval -> durable job -> ZIP with
canonical manifest -> short-lived, user-bound download.

Policy (the existing approval model is reused, no new bypass):
* who may request: roles with ``approvals:request`` (operator, tenant admin) on a case they can
  see; who may approve: a *different* tenant admin (``approvals:decide`` + fresh MFA), through
  the existing ``POST /api/approvals/{id}/approve``;
* scope is fixed at request time: every evidence item of the case, redacted variant. The
  unredacted original is added only if ``include_original`` was asked AND each item has a
  separately stored original AND the requester holds an active unblur grant for each (checked
  at request and again at generation). Otherwise the request is refused, never downgraded;
* purged or missing evidence fails the request (410) instead of being silently left out;
* the package can be downloaded only by its requester, only while the approval grant is
  active (``expires_at`` = grant expiry); afterwards it is deleted and answers 410.

Job semantics: one row in ``export_jobs``. Claiming is a single
``UPDATE ... WHERE id = (SELECT ... FOR UPDATE SKIP LOCKED)``; a job whose lease expired
(worker crashed) is claimable again and restarts from zero (attempt + 1, new temp file, new
storage key), up to ``MAX_ATTEMPTS``. Completion is conditional on still owning the attempt.
A storage outage (the store did not answer, while reading evidence or uploading the package)
is not a verdict on the job: it is retried after ``STORAGE_BACKOFF`` without consuming an
attempt, up to ``MAX_STORAGE_RETRIES`` outages, and only then fails.

Legal hold (``case_legal_holds``): while the case is held a completed or revoked package is
never deleted and never moved to ``expired``; access rules do not change (download still needs
the live approval grant). Releasing the hold runs the normal expiry for that case.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import time
import uuid
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import and_, exists, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import AuditAction
from app.core.catalog import ACTIONS, EVENT_TYPES
from app.models import (
    Alert,
    ApprovalKind,
    ApprovalRequest,
    ApprovalStatus,
    AuditLog,
    Camera,
    CaseLegalHold,
    Evidence,
    ExportJob,
    ExportState,
    User,
)
from app.schemas.investigation import ExportIn
from app.services import approvals, camera_control, casework
from app.services import evidence as evidence_service
from app.services.investigation import audit_case, case_evidence, provenance
from app.services.package_verify import SCHEMA, SCHEMA_VERSION, canonical_json

log = logging.getLogger("app.exports")

LEASE = timedelta(minutes=5)
MAX_ATTEMPTS = 3
MAX_STORAGE_RETRIES = 10
STORAGE_BACKOFF = timedelta(seconds=30)
MAX_PACKAGE_BYTES = 512 * 1024 * 1024
TEMP_PREFIX = "rs-export-"
ZIP_DATE = (1980, 1, 1, 0, 0, 0)  # fixed entry timestamps: no wall-clock leaks into the zip
EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "video/mp4": "mp4"}
INTEGRITY_NOTE = (
    "Unsigned package. Integrity is checked with the per-file SHA-256 digests in this manifest "
    "and the SHA-256 of manifest.json, which RoadSentinel records in its hash-chained audit log "
    "(action export.generated). Those records live on the same system: they are tamper-evident, "
    "not independent legal custody. No signature key-custody model is defined."
)
DISCLAIMER = (
    "Decision-support material from an automated detector. A human decision is recorded below; "
    "detections are not ground truth, speeds are uncalibrated estimates, and RoadSentinel "
    "issues no fines and contacts no enforcement or dispatch system."
)
VERIFY_TXT = """RoadSentinel evidence package - verification
=============================================

1. Get the manifest digest from RoadSentinel (case page -> export, or the audit log entry
   "export.generated" for this package). Do not trust a digest found inside this zip.
2. Compute the SHA-256 of manifest.json and compare:
       sha256sum manifest.json          (Linux)
       shasum -a 256 manifest.json      (macOS)
3. For every entry in manifest.json "files", compute the SHA-256 of the file at "path" and
   compare it with "sha256"; compare the byte size with "size_bytes". No other files may exist
   besides manifest.json and this VERIFY.txt.
4. Or run the bundled verifier (standard library only, no network, no keys):
       python -m app.cli verify-package <package.zip> --manifest-sha256 <digest>

The package is NOT signed. See manifest.json "integrity" for what the digests do and do not
prove.
"""


class ExportError(Exception):
    def __init__(self, status_code: int, message: str, code: str) -> None:
        super().__init__(message)
        self.status_code, self.message, self.code = status_code, message, code


def _now() -> datetime:
    return datetime.now(UTC)


def package_key(job: ExportJob, attempt: int) -> str:
    return f"{job.tenant_id}/exports/{job.id}.{attempt}.zip.enc"


def package_key_id(job: ExportJob) -> uuid.UUID:
    return uuid.uuid5(job.id, "export-package")


# --------------------------------------------------------------------------- request


def _check_scope(
    db: Session, files: list[Evidence], requester_id: uuid.UUID, include_original: bool
) -> None:
    if not files:
        raise ExportError(422, "Cazul nu are probe de exportat.", "no_evidence")
    for ev in files:
        if ev.purged_at is not None:
            raise ExportError(410, "O probă a cazului a fost purjată.", "evidence_purged")
        state = evidence_service.storage_state(ev)
        if state == "unavailable":
            raise evidence_service.StorageUnavailableError(str(ev.id))
        if state != "available":
            raise ExportError(410, "Fișierul unei probe lipsește din stocare.", "evidence_missing")
        if not include_original:
            continue
        if not evidence_service.has_distinct_original(ev):
            raise ExportError(
                422,
                "Nu există original nemascat pentru toate probele; exportul nemascat este refuzat.",
                "original_unavailable",
            )
        if not evidence_service.object_exists(evidence_service.storage_key(ev, "original")):
            raise ExportError(
                410, "Originalul unei probe lipsește din stocare.", "evidence_missing"
            )
        if not approvals.active_grant(
            db, kind=ApprovalKind.unblur, resource_id=ev.id, user_id=requester_id
        ):
            raise ExportError(
                403,
                "Exportul nemascat cere o aprobare activă de demascare pentru fiecare probă.",
                "unblur_grant_required",
            )


def check_source_grant(db: Session, camera_id: uuid.UUID | None) -> None:
    """A managed camera needs a current grant that allows export; legacy cameras have none."""
    camera = db.get(Camera, camera_id) if camera_id else None
    if camera is None or camera.lifecycle_state == "legacy":
        return
    if not camera_control.grant_allows_export(
        camera, camera_control.grants_for(db, camera.id), _now()
    ):
        raise ExportError(
            403,
            "Autorizarea sursei camerei nu permite exportul sau a expirat.",
            "source_grant_required",
        )


def request_export(
    db: Session, *, alert: Alert, requester_id: uuid.UUID, body: ExportIn
) -> tuple[ExportJob, bool]:
    """Create (or, for a repeated idempotency key, return) the export request and its pending
    four-eyes approval. Returns (job, created)."""
    existing = db.scalar(
        select(ExportJob).where(
            ExportJob.requester_id == requester_id,
            ExportJob.idempotency_key == body.idempotency_key,
        )
    )
    if existing is not None:
        if existing.alert_id != alert.id or existing.include_original != body.include_original:
            raise ExportError(409, "Cheia de idempotență a fost folosită altfel.", "key_reused")
        return existing, False
    check_source_grant(db, alert.camera_id)
    files = case_evidence(db, alert)
    _check_scope(db, files, requester_id, body.include_original)
    job = ExportJob(
        id=uuid.uuid4(),
        tenant_id=alert.tenant_id,
        alert_id=alert.id,
        requester_id=requester_id,
        idempotency_key=body.idempotency_key,
        include_original=body.include_original,
        evidence_ids=sorted(str(ev.id) for ev in files),
        state=ExportState.pending_approval.value,
    )
    db.add(job)
    try:
        db.flush()
    except IntegrityError:
        # A concurrent request with the same key won the unique constraint.
        db.rollback()
        return request_export(db, alert=alert, requester_id=requester_id, body=body)
    req = approvals.create_request(
        db,
        tenant_id=alert.tenant_id,
        kind=ApprovalKind.export,
        resource_type="export_jobs",
        resource_id=job.id,
        requester_id=requester_id,
        justification=body.justification,
        case_reference=body.case_reference,
    )
    job.approval_id = req.id
    db.commit()
    return job, True


def on_approval_decided(db: Session, req: ApprovalRequest) -> ExportJob | None:
    """Hook called by the approvals API after approve/deny/revoke. Moves the linked job."""
    if req.resource_type != "export_jobs":
        return None
    job = db.get(ExportJob, req.resource_id)
    if job is None:
        return None
    transitions = {
        ApprovalStatus.approved: ([ExportState.pending_approval], ExportState.queued),
        ApprovalStatus.denied: ([ExportState.pending_approval], ExportState.denied),
        ApprovalStatus.revoked: (
            [ExportState.pending_approval, ExportState.queued, ExportState.completed],
            ExportState.canceled,
        ),
    }
    if req.status not in transitions:
        return None
    sources, target = transitions[req.status]
    values: dict[str, Any] = {"state": target.value}
    if req.status == ApprovalStatus.approved:
        values["expires_at"] = req.grant_expires_at
    db.execute(
        update(ExportJob)
        .where(ExportJob.id == job.id, ExportJob.state.in_([x.value for x in sources]))
        .values(**values)
    )
    db.commit()
    db.refresh(job)
    if job.state == ExportState.canceled.value and job.package_key:
        _drop_canceled_package(db, job)
    return job


def _drop_canceled_package(db: Session, job: ExportJob) -> bool:
    """Delete a canceled job's package, unless the case is under legal hold (kept; the sweep
    deletes it after release). Clears ``package_key`` so it is deleted once."""
    if not job.package_key or casework.is_held(db, job.alert_id):
        return False
    _delete_package(job)
    job.package_key = None
    db.commit()
    return True


def cancel(db: Session, job: ExportJob, actor_id: uuid.UUID, is_admin: bool) -> ExportJob:
    if job.requester_id != actor_id and not is_admin:
        raise ExportError(403, "Doar solicitantul sau un administrator poate anula.", "forbidden")
    done = db.execute(
        update(ExportJob)
        .where(
            ExportJob.id == job.id,
            ExportJob.state.in_([ExportState.pending_approval.value, ExportState.queued.value]),
        )
        .values(state=ExportState.canceled.value)
        .returning(ExportJob.id)
    ).first()
    if done is None:
        db.rollback()
        raise ExportError(409, "Exportul nu mai poate fi anulat în starea curentă.", "bad_state")
    req = db.get(ApprovalRequest, job.approval_id) if job.approval_id else None
    if req is not None and req.status in (ApprovalStatus.pending, ApprovalStatus.approved):
        approvals.revoke(db, req)
    db.commit()
    db.refresh(job)
    return job


# --------------------------------------------------------------------------- jobs


def claim(db: Session, worker_id: str, job_id: uuid.UUID | None = None) -> ExportJob | None:
    """Atomically take one runnable job (queued, or processing with an expired lease)."""
    now = _now()
    runnable = select(ExportJob.id).where(
        or_(
            ExportJob.state == ExportState.queued.value,
            and_(
                ExportJob.state == ExportState.processing.value,
                ExportJob.lease_expires_at < now,
            ),
        ),
        ExportJob.attempt < MAX_ATTEMPTS,
    )
    if job_id is not None:
        runnable = runnable.where(ExportJob.id == job_id)
    target = (
        runnable.order_by(ExportJob.created_at).limit(1).with_for_update(skip_locked=True)
    ).scalar_subquery()
    row = db.execute(
        update(ExportJob)
        .where(ExportJob.id == target)
        .values(
            state=ExportState.processing.value,
            attempt=ExportJob.attempt + 1,
            worker_id=worker_id[:64],
            lease_expires_at=now + LEASE,
            heartbeat_at=now,
            started_at=now,
            error=None,
        )
        .returning(ExportJob.id)
    ).first()
    db.commit()
    if row is None:
        return None
    job = db.get(ExportJob, row[0])
    if job is not None:
        db.refresh(job)
    return job


def fail_exhausted(db: Session) -> list[ExportJob]:
    """Jobs whose last allowed attempt died with the lease: mark them failed (not retried)."""
    rows = db.scalars(
        update(ExportJob)
        .where(
            ExportJob.state == ExportState.processing.value,
            ExportJob.lease_expires_at < _now(),
            ExportJob.attempt >= MAX_ATTEMPTS,
        )
        .values(state=ExportState.failed.value, error="attempts_exhausted")
        .returning(ExportJob)
    ).all()
    db.commit()
    return list(rows)


def _heartbeat(db: Session, job: ExportJob, attempt: int) -> None:
    now = _now()
    owned = db.execute(
        update(ExportJob)
        .where(
            ExportJob.id == job.id,
            ExportJob.state == ExportState.processing.value,
            ExportJob.attempt == attempt,
        )
        .values(heartbeat_at=now, lease_expires_at=now + LEASE)
        .returning(ExportJob.id)
    ).first()
    db.commit()
    if owned is None:
        raise ExportError(409, "Lease lost to another worker.", "lease_lost")


def _audit_refs(db: Session, alert: Alert) -> list[dict[str, Any]]:
    wanted = [
        AuditAction.alert_created.value,
        AuditAction.alert_confirmed.value,
        AuditAction.alert_rejected.value,
    ]
    rows = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.resource_type == "alerts",
            AuditLog.resource_id == str(alert.id),
            AuditLog.action.in_(wanted),
        )
        .order_by(AuditLog.seq)
    )
    return [
        {
            "seq": e.seq,
            "action": e.action,
            "at": e.ts.astimezone(UTC).isoformat(),
            "entry_hash": e.entry_hash,
        }
        for e in rows
    ]


def build_manifest(
    db: Session,
    job: ExportJob,
    alert: Alert,
    camera: Camera,
    approval: ApprovalRequest,
    files: list[dict[str, Any]],
) -> dict[str, Any]:
    from app.services.incident_map import alert_location
    location_snapshot = alert_location(db, alert)
    requester = db.get(User, job.requester_id)
    prov = provenance(alert)
    observed = alert.detected_at.astimezone(UTC)
    from zoneinfo import ZoneInfo

    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "package_id": str(job.id),
        "geographic_attribution": json.loads(json.dumps(location_snapshot, default=str)),
        "generated_at": _now().isoformat(),
        "tenant_id": str(job.tenant_id),
        "exporter": {
            "user_id": str(job.requester_id),
            "role": requester.role.value if requester else None,
        },
        "approval": {
            "request_id": str(approval.id),
            "approved_by": str(approval.decided_by) if approval.decided_by else None,
            "approved_at": approval.decided_at.isoformat() if approval.decided_at else None,
            "grant_expires_at": (
                approval.grant_expires_at.isoformat() if approval.grant_expires_at else None
            ),
            "case_reference": approval.case_reference,
        },
        "case": {
            "number": alert.number,
            "alert_id": str(alert.id),
            "event_type": alert.event_type,
            "event_label": EVENT_TYPES.get(alert.event_type, (None, alert.event_type))[1],
            "priority": alert.priority.value,
            "observed_at_utc": observed.isoformat(),
            "observed_at_local": observed.astimezone(ZoneInfo(camera.timezone)).isoformat(),
            "timezone": camera.timezone,
            "camera": {"id": str(camera.id), "slug": camera.slug, "name": camera.name},
            "source_kind": prov.source_kind,
            "rule": alert.rule or alert.description,
            "recorded_details": prov.recorded_details,
            "model": (
                {"id": prov.model_id, "hash": prov.model_hash}
                if prov.model_status == "recorded"
                else None
            ),
            "speed_kmh": alert.speed_kmh,
            "speed_status": prov.speed_status,
            "track_id": alert.track_id,
            "object_class": alert.object_class,
            "video_t_s": alert.video_t,
        },
        "decision": {
            "status": alert.status.value,
            "action": alert.action,
            "action_label": ACTIONS.get(alert.action or ""),
            "decided_by": str(alert.decided_by) if alert.decided_by else None,
            "decided_at": alert.decided_at.isoformat() if alert.decided_at else None,
            "audit_refs": _audit_refs(db, alert),
        },
        "scope": {"variants": ["original", "redacted"] if job.include_original else ["redacted"]},
        "files": sorted(files, key=lambda f: f["path"]),
        "integrity": {"algorithm": "sha256", "signature": None, "note": INTEGRITY_NOTE},
        "disclaimer": DISCLAIMER,
    }


def _write_entry(
    zf: zipfile.ZipFile,
    path: str,
    chunks: Any,
    budget: list[int],
) -> tuple[str, int]:
    info = zipfile.ZipInfo(path, date_time=ZIP_DATE)
    info.compress_type = zipfile.ZIP_STORED  # media is already compressed
    digest, size = hashlib.sha256(), 0
    with zf.open(info, "w", force_zip64=True) as out:
        for chunk in chunks:
            size += len(chunk)
            budget[0] += len(chunk)
            if budget[0] > MAX_PACKAGE_BYTES:
                raise ExportError(413, "Pachetul depășește dimensiunea maximă.", "too_large")
            digest.update(chunk)
            out.write(chunk)
    return digest.hexdigest(), size


def process(db: Session, keyring: Any, job: ExportJob) -> ExportJob:
    """Generate the package for a job this worker has just claimed. Never raises for job-level
    failures: they end in state ``failed`` with a sanitized error code (and an audit entry)."""
    attempt = job.attempt
    alert = db.get(Alert, job.alert_id)
    assert alert is not None
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"{TEMP_PREFIX}{job.id}-{attempt}-"))
    key = package_key(job, attempt)
    stored = False
    try:
        approval = db.get(ApprovalRequest, job.approval_id) if job.approval_id else None
        if approval is None or not approvals.is_grant_active(approval):
            raise ExportError(410, "Aprobarea exportului a expirat.", "approval_expired")
        camera = db.get(Camera, alert.camera_id)
        assert camera is not None
        files = [db.get(Evidence, uuid.UUID(i)) for i in job.evidence_ids]
        if any(ev is None or ev.alert_id != alert.id for ev in files):
            raise ExportError(409, "Setul de probe s-a schimbat.", "scope_changed")
        evs = [ev for ev in files if ev is not None]
        _check_scope(db, evs, job.requester_id, job.include_original)

        variants = ["redacted", "original"] if job.include_original else ["redacted"]
        entries: list[dict[str, Any]] = []
        budget = [0]
        tmp_zip = tmp_dir / "package.zip"
        with zipfile.ZipFile(tmp_zip, "w", allowZip64=True) as zf:
            for ev in sorted(evs, key=lambda e: (e.kind, str(e.id))):
                ext = EXTENSIONS.get(ev.content_type, "bin")
                for variant in variants:
                    path = f"evidence/{ev.kind}-{ev.id}.{variant}.{ext}"
                    try:
                        sha, size = _write_entry(
                            zf, path, evidence_service.open_decrypted(keyring, ev, variant), budget
                        )
                    except FileNotFoundError as exc:
                        raise ExportError(
                            410, "Fișierul unei probe lipsește.", "evidence_missing"
                        ) from exc
                    entries.append(
                        {
                            "path": path,
                            "evidence_id": str(ev.id),
                            "kind": ev.kind,
                            "variant": variant,
                            "media_type": ev.content_type,
                            "redaction": ev.redaction if variant == "redacted" else "none",
                            "size_bytes": size,
                            "sha256": sha,
                            # The ingest hash covers the stored original only.
                            "matches_ingest_sha256": (
                                sha == ev.sha256
                                if variant == "original"
                                or not evidence_service.has_distinct_original(ev)
                                else None
                            ),
                        }
                    )
                    _heartbeat(db, job, attempt)
            manifest = canonical_json(build_manifest(db, job, alert, camera, approval, entries))
            for name, data in (("manifest.json", manifest), ("VERIFY.txt", VERIFY_TXT.encode())):
                info = zipfile.ZipInfo(name, date_time=ZIP_DATE)
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, data)
        manifest_sha = hashlib.sha256(manifest).hexdigest()
        with open(tmp_zip, "rb") as fh:
            package_sha = hashlib.file_digest(fh, "sha256").hexdigest()  # streamed, bounded memory
        size = tmp_zip.stat().st_size
        with open(tmp_zip, "rb") as fh:
            evidence_service.write_encrypted_stream(keyring, package_key_id(job), fh, key)
        stored = True
        done = db.execute(
            update(ExportJob)
            .where(
                ExportJob.id == job.id,
                ExportJob.state == ExportState.processing.value,
                ExportJob.attempt == attempt,
            )
            .values(
                state=ExportState.completed.value,
                completed_at=_now(),
                expires_at=approval.grant_expires_at,
                manifest_sha256=manifest_sha,
                package_sha256=package_sha,
                package_key=key,
                package_size=size,
                file_count=len(entries),
                lease_expires_at=None,
                error=None,
            )
            .returning(ExportJob.id)
        ).first()
        db.commit()
        if done is None:
            raise ExportError(409, "Lease lost to another worker.", "lease_lost")
        stored = False  # committed: the package now belongs to the completed job
        db.refresh(job)
        _audit_outcome(
            job,
            AuditAction.export_generated,
            alert,
            attempt=attempt,
            manifest_sha256=manifest_sha,
            package_sha256=package_sha,
            files=len(entries),
            bytes=size,
            variants=variants,
        )
        return job
    except Exception as exc:
        db.rollback()
        if stored:
            try:
                evidence_service.delete_object(key)
            except Exception:  # best-effort cleanup, logged
                log.warning("export cleanup failed", extra={"export_id": str(job.id)})
        if isinstance(exc, evidence_service.StorageUnavailableError):
            # An outage is not a verdict on the job: give the attempt back and retry after a
            # short backoff, within a separate bounded budget of outages.
            if job.storage_retries + 1 <= MAX_STORAGE_RETRIES:
                db.execute(
                    update(ExportJob)
                    .where(
                        ExportJob.id == job.id,
                        ExportJob.state == ExportState.processing.value,
                        ExportJob.attempt == attempt,
                    )
                    .values(
                        attempt=ExportJob.attempt - 1,
                        storage_retries=ExportJob.storage_retries + 1,
                        lease_expires_at=_now() + STORAGE_BACKOFF,
                        error="storage_unavailable",
                    )
                )
                db.commit()
                db.refresh(job)
                return job
            exc = ExportError(503, "Stocarea a fost indisponibilă prea des.", "storage_unavailable")
        code = exc.code if isinstance(exc, ExportError) else "internal_error"
        if not isinstance(exc, ExportError):
            log.error("export failed", exc_info=exc, extra={"export_id": str(job.id)})
        if code != "lease_lost":
            db.execute(
                update(ExportJob)
                .where(
                    ExportJob.id == job.id,
                    ExportJob.state == ExportState.processing.value,
                    ExportJob.attempt == attempt,
                )
                .values(state=ExportState.failed.value, error=code, lease_expires_at=None)
            )
            db.commit()
            _audit_outcome(job, AuditAction.export_failed, alert, attempt=attempt, error=code)
        db.refresh(job)
        return job
    finally:
        for p in tmp_dir.glob("*"):
            p.unlink(missing_ok=True)
        tmp_dir.rmdir()


def _audit_outcome(job: ExportJob, action: AuditAction, alert: Alert, **details: Any) -> None:
    """Record a job outcome that is already committed. A failure here must not change the job
    or delete its package, so it is logged for the operators instead of raised."""
    try:
        audit_case(job.tenant_id, job.requester_id, action, alert, export_id=str(job.id), **details)
    except Exception as exc:
        log.error("export audit failed", exc_info=exc, extra={"export_id": str(job.id)})


def cleanup_stale_temp(max_age: timedelta = LEASE * 2) -> int:
    """Remove temp package dirs left by crashed workers (older than two leases)."""
    removed = 0
    cutoff = time.time() - max_age.total_seconds()
    for d in Path(tempfile.gettempdir()).glob(f"{TEMP_PREFIX}*"):
        if d.is_dir() and d.stat().st_mtime < cutoff:
            for p in d.glob("*"):
                p.unlink(missing_ok=True)
            d.rmdir()
            removed += 1
    return removed


# --------------------------------------------------------------------------- download


def _delete_package(job: ExportJob) -> None:
    if job.package_key:
        try:
            evidence_service.delete_object(job.package_key)
        except Exception:
            log.warning("package delete failed", extra={"export_id": str(job.id)})


def expire_if_due(db: Session, job: ExportJob) -> bool:
    """Completed package past its window: delete it and mark expired. True if it expired now."""
    if job.state != ExportState.completed.value or not job.expires_at:
        return False
    if job.expires_at > _now():
        return False
    if casework.is_held(db, job.alert_id):
        return False  # legal hold: kept past its window, still not downloadable without a grant
    done = db.execute(
        update(ExportJob)
        .where(ExportJob.id == job.id, ExportJob.state == ExportState.completed.value)
        .values(state=ExportState.expired.value)
        .returning(ExportJob.id)
    ).first()
    db.commit()
    db.refresh(job)
    if done is not None:
        _delete_package(job)
        return True
    return False


def _not_held() -> Any:
    return ~exists().where(
        CaseLegalHold.alert_id == ExportJob.alert_id, CaseLegalHold.released_at.is_(None)
    )


def expire_due(db: Session, alert_id: uuid.UUID | None = None) -> list[ExportJob]:
    """Worker sweep: packages past their window are deleted even if nobody asks for them, and
    packages of revoked jobs kept by a (since released) legal hold are deleted. Cases under
    legal hold are skipped. Returns the jobs that expired now."""
    scope = [ExportJob.alert_id == alert_id] if alert_id is not None else []
    due = db.scalars(
        select(ExportJob).where(
            ExportJob.state == ExportState.completed.value,
            ExportJob.expires_at < _now(),
            _not_held(),
            *scope,
        )
    ).all()
    expired = [job for job in due if expire_if_due(db, job)]
    kept = db.scalars(
        select(ExportJob).where(
            ExportJob.state == ExportState.canceled.value,
            ExportJob.package_key.is_not(None),
            _not_held(),
            *scope,
        )
    ).all()
    for job in kept:
        _drop_canceled_package(db, job)
    return expired


def check_downloadable(db: Session, job: ExportJob, user_id: uuid.UUID) -> None:
    if job.requester_id != user_id:
        raise ExportError(403, "Doar solicitantul poate descărca pachetul.", "not_requester")
    if job.state == ExportState.expired.value:
        raise ExportError(410, "Pachetul a expirat și a fost șters.", "expired")
    if job.state != ExportState.completed.value or not job.package_key:
        raise ExportError(409, "Pachetul nu este gata.", "not_ready")
    approval = db.get(ApprovalRequest, job.approval_id) if job.approval_id else None
    if approval is None or not approvals.is_grant_active(approval):
        raise ExportError(410, "Aprobarea exportului a expirat sau a fost revocată.", "expired")
    alert = db.get(Alert, job.alert_id)
    if alert is not None:
        check_source_grant(db, alert.camera_id)
    for i in job.evidence_ids:
        ev = db.get(Evidence, uuid.UUID(i))
        if ev is None or ev.purged_at is not None:
            raise ExportError(410, "O probă din pachet a fost purjată.", "evidence_purged")
        if job.include_original and not approvals.active_grant(
            db, kind=ApprovalKind.unblur, resource_id=ev.id, user_id=user_id
        ):
            raise ExportError(
                403,
                "Aprobarea de demascare a expirat sau a fost revocată.",
                "unblur_grant_required",
            )


def open_package(keyring: Any, job: ExportJob) -> Any:
    assert job.package_key
    return evidence_service.open_decrypted_key(keyring, package_key_id(job), job.package_key)


def worker_id() -> str:
    return f"{os.uname().nodename[:40]}:{os.getpid()}"
