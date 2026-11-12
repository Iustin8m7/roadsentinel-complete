"""Tamper-evident audit log: one SHA-256 hash chain per tenant.

``entry_hash = SHA-256(canonical_json(tenant_id, seq, timestamp, actor_id, action,
resource_type, resource_id, ip, user_agent, details, prev_hash))``

Entries are written in their *own* short transaction (committed immediately), so that denied
or failed actions are still recorded even when the request's own transaction rolls back. A
per-tenant advisory lock serializes writers so ``seq`` stays gap-free.
"""

from __future__ import annotations

import enum
import hashlib
import json
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.redaction import redact
from app.db import tenant_session
from app.models import AuditLog

GENESIS_HASH = "0" * 64


class AuditAction(enum.StrEnum):
    security_configuration_changed = "security.configuration.changed"
    login_success = "auth.login.success"
    login_failure = "auth.login.failure"
    login_locked = "auth.login.locked"
    mfa_enroll_start = "auth.mfa.enroll_start"
    mfa_enrolled = "auth.mfa.enrolled"
    mfa_success = "auth.mfa.success"
    mfa_failure = "auth.mfa.failure"
    recovery_code_used = "auth.mfa.recovery_code_used"
    reauth_success = "auth.reauth.success"
    reauth_failure = "auth.reauth.failure"
    logout = "auth.logout"
    refresh_reuse = "auth.refresh.reuse_detected"
    session_revoked = "auth.session.revoked"
    rate_limited = "auth.rate_limited"
    invitation_created = "user.invitation.created"
    invitation_revoked = "user.invitation.revoked"
    invitation_accepted = "user.invitation.accepted"
    invitation_failure = "user.invitation.failure"
    account_reset_requested = "user.reset.requested"
    account_reset_issued = "user.reset.issued"
    account_reset_completed = "user.reset.completed"
    account_reset_failure = "user.reset.failure"
    password_changed = "user.password.changed"  # noqa: S105
    sessions_revoked_bulk = "auth.sessions.revoked_bulk"
    user_updated = "user.updated"
    tenant_created = "tenant.created"
    camera_created = "camera.created"
    camera_updated = "camera.updated"
    camera_worker_started = "camera.worker.started"
    camera_worker_stopped = "camera.worker.stopped"
    camera_worker_restarted = "camera.worker.restarted"
    recording_imported = "recording.imported"
    analysis_started = "recorded_analysis.started"
    analysis_cancelled = "recorded_analysis.cancelled"
    analysis_analytics_viewed = "recorded_analysis.analytics.viewed"
    recording_crop_updated = "recording.crop.updated"
    alert_created = "alert.created"
    alert_confirmed = "alert.confirmed"
    alert_rejected = "alert.rejected"
    alert_assigned = "alert.assigned"
    patrol_status = "alert.patrol_status"
    alert_plate_search = "alert.plate_search"
    evidence_url_issued = "evidence.url_issued"
    evidence_viewed = "evidence.viewed"
    evidence_exported = "evidence.exported"
    approval_requested = "approval.requested"
    approval_approved = "approval.approved"
    approval_denied = "approval.denied"
    approval_revoked = "approval.revoked"
    approval_self_approval_blocked = "approval.self_approval_blocked"
    key_rotated = "crypto.key_rotated"
    keys_rewrapped = "crypto.keys_rewrapped"
    cross_tenant_access = "security.cross_tenant_access"
    access_denied = "security.access_denied"
    csrf_failure = "security.csrf_failure"
    audit_verified = "audit.verified"
    push_subscribed = "push.subscribed"
    service_account_created = "service.account.created"
    service_account_updated = "service.account.updated"
    service_key_issued = "service.key.issued"
    service_key_revoked = "service.key.revoked"
    ingest_auth_failure = "ingest.auth.failure"
    ingest_replay = "ingest.auth.replay"
    ingest_rate_limited = "ingest.rate_limited"
    ingest_camera_video = "ingest.camera_video"
    ingest_camera_superseded = "ingest.camera_superseded"
    ingest_camera_clear_denied = "ingest.camera_clear_denied"
    alert_viewed = "alert.viewed"
    alert_vlm_verdict = "alert.vlm_verdict"
    alert_search = "alert.search"
    saved_search_created = "alert.saved_search.created"
    saved_search_updated = "alert.saved_search.updated"
    saved_search_deleted = "alert.saved_search.deleted"
    retention_policy_changed = "retention.policy_changed"
    retention_purged = "retention.purged"
    legal_hold_set = "alert.legal_hold_set"
    legal_hold_released = "alert.legal_hold_released"

    camera_lifecycle_changed = 'camera.lifecycle_changed'
    camera_source_set = 'camera.source.set'
    camera_grant_created = 'camera.grant.created'
    camera_grant_revoked = 'camera.grant.revoked'
    camera_config_drafted = 'camera.config.drafted'
    camera_config_validated = 'camera.config.validated'
    camera_config_submitted = 'camera.config.submitted'
    camera_config_approved = 'camera.config.approved'
    camera_config_rejected = 'camera.config.rejected'
    camera_config_activated = 'camera.config.activated'
    camera_config_rolled_back = 'camera.config.rolled_back'
    camera_paused = 'camera.paused'
    camera_resumed = 'camera.resumed'
    camera_disabled = 'camera.disabled'
    camera_enable_requested = 'camera.enable_requested'
    camera_enabled = 'camera.enabled'
    camera_control_refused = 'camera.control.refused'
    camera_worker_ack = 'camera.worker.ack'
    camera_worker_conflict = 'camera.worker.conflict'
    ingest_camera_blocked = 'ingest.camera_blocked'
    alert_decision_conflict = 'alert.decision_conflict'
    case_note_created = 'case.note.created'
    case_note_revised = 'case.note.revised'
    case_note_retracted = 'case.note.retracted'
    case_bookmark_created = 'case.bookmark.created'
    case_bookmark_removed = 'case.bookmark.removed'
    evidence_missing = 'evidence.missing'
    evidence_purged = 'evidence.purged'
    export_requested = 'export.requested'
    export_queued = 'export.queued'
    export_denied = 'export.denied'
    export_canceled = 'export.canceled'
    export_generated = 'export.generated'
    export_failed = 'export.failed'
    export_link_issued = 'export.link_issued'
    export_downloaded = 'export.downloaded'
    export_expired = 'export.expired'
    camera_failure_notified = 'camera.failure.notified'
    case_link_created = 'case.link.created'
    case_link_removed = 'case.link.removed'
    case_followup_created = 'case.followup.created'
    case_followup_updated = 'case.followup.updated'
    legal_hold_placed = 'case.legal_hold.placed'
    evidence_purge_refused = 'evidence.purge_refused'
    package_verified = 'export.package_verified'
    evidence_integrity_checked = 'audit.evidence_integrity_checked'

@dataclass
class RequestContext:
    ip: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


request_context: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


def _iso(ts: datetime) -> str:
    return ts.astimezone(UTC).isoformat(timespec="microseconds")


def _clean_details(details: dict[str, Any] | None) -> dict[str, Any]:
    # Redact secrets, then force a JSON-stable shape (jsonb must round-trip identically).
    cleaned = redact(details or {})
    result: dict[str, Any] = json.loads(json.dumps(cleaned, default=str, sort_keys=True))
    return result


def canonical_bytes(
    *,
    tenant_id: uuid.UUID,
    seq: int,
    ts: datetime,
    actor_id: uuid.UUID | None,
    action: str,
    resource_type: str | None,
    resource_id: str | None,
    ip: str | None,
    user_agent: str | None,
    details: dict[str, Any],
    prev_hash: str,
) -> bytes:
    doc = {
        "tenant_id": str(tenant_id),
        "seq": seq,
        "timestamp": _iso(ts),
        "actor_id": str(actor_id) if actor_id else None,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "ip": ip,
        "user_agent": user_agent,
        "details": details,
        "prev_hash": prev_hash,
    }
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def compute_hash(entry: AuditLog) -> str:
    return hashlib.sha256(
        canonical_bytes(
            tenant_id=entry.tenant_id,
            seq=entry.seq,
            ts=entry.ts,
            actor_id=entry.actor_id,
            action=entry.action,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            ip=entry.ip,
            user_agent=entry.user_agent,
            details=entry.details,
            prev_hash=entry.prev_hash,
        )
    ).hexdigest()


def append(
    db: Session,
    tenant_id: uuid.UUID,
    action: AuditAction | str,
    *,
    actor_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: object | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Append to the chain inside ``db``'s current transaction (caller commits)."""
    ctx = request_context.get() or RequestContext()
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:tid, 7))"), {"tid": str(tenant_id)}
    )
    last = db.execute(
        select(AuditLog.seq, AuditLog.entry_hash)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.seq.desc())
        .limit(1)
    ).first()
    seq, prev_hash = (last[0] + 1, last[1]) if last else (1, GENESIS_HASH)
    entry = AuditLog(
        tenant_id=tenant_id,
        seq=seq,
        ts=datetime.now(UTC),
        actor_id=actor_id,
        action=str(action),
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        ip=ctx.ip,
        user_agent=(ctx.user_agent or None) and ctx.user_agent[:400],
        details=_clean_details(details),
        prev_hash=prev_hash,
    )
    entry.entry_hash = compute_hash(entry)
    db.add(entry)
    db.flush()
    return entry


def record(
    tenant_id: uuid.UUID,
    action: AuditAction | str,
    *,
    actor_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: object | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Append in an independent, immediately committed transaction."""
    with tenant_session(tenant_id) as db:
        append(
            db,
            tenant_id,
            action,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )
        db.commit()


def platform_tenant_id(db: Session) -> uuid.UUID | None:
    """Tenant whose chain receives events that cannot be attributed to a tenant
    (e.g. failed logins for unknown accounts)."""
    value = db.execute(text("SELECT rs_platform_tenant()")).scalar()
    return value if isinstance(value, uuid.UUID) else None


@dataclass
class VerifyResult:
    ok: bool
    checked: int
    first_broken_seq: int | None = None
    first_broken_id: int | None = None
    reason: str | None = None
    head_hash: str | None = None


def verify_chain(db: Session, tenant_id: uuid.UUID) -> VerifyResult:
    """Walk the tenant's chain in ``seq`` order and report the first inconsistency."""
    expected_seq, prev = 1, GENESIS_HASH
    checked = 0
    rows = db.scalars(
        select(AuditLog).where(AuditLog.tenant_id == tenant_id).order_by(AuditLog.seq, AuditLog.id)
    )
    for entry in rows:
        checked += 1
        if entry.seq != expected_seq:
            return VerifyResult(False, checked, entry.seq, entry.id, "sequence gap or reorder")
        if entry.prev_hash != prev:
            return VerifyResult(False, checked, entry.seq, entry.id, "prev_hash mismatch")
        if compute_hash(entry) != entry.entry_hash:
            return VerifyResult(False, checked, entry.seq, entry.id, "entry_hash mismatch")
        prev = entry.entry_hash
        expected_seq += 1
    return VerifyResult(True, checked, head_hash=prev if checked else None)
