"""Retention of evidence: per-tenant days per kind, legal hold, dry-run, audited purge.

What a purge does: deletes the encrypted file(s) and marks the evidence row ``purged_at``. The row
(kind, size, sha256, timestamps) stays so chain-of-custody questions can still be answered; the
alert and its audit trail are NOT deleted by this job. Items of an alert under legal hold are never
purged.
Not covered: the audit log itself keeps ip / user agent / decision notes (see docs/LIMITS.md).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.audit import AuditAction
from app.models import Alert, AlertStatus, Evidence, RetentionPolicy
from app.services import evidence as evidence_service

# Defaults when a tenant has set nothing: short for unreviewed video, longer for confirmed cases.
DEFAULT_DAYS = {"keyframe": 30, "clip": 30, "camera_video": 7, "confirmed_case": 365}
MAX_IDS_IN_AUDIT = 200


@dataclass
class PurgeReport:
    dry_run: bool
    candidates: int = 0
    purged: int = 0
    files_removed: int = 0
    held_skipped: int = 0
    errors: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)
    ids: list[str] = field(default_factory=list)


def _now() -> datetime:
    return datetime.now(UTC)


def policy(db: Session) -> dict[str, int]:
    rows = {p.kind: p.days for p in db.scalars(select(RetentionPolicy))}
    return {k: rows.get(k, d) for k, d in DEFAULT_DAYS.items()}


def set_policy(
    db: Session, tenant_id: uuid.UUID, days: dict[str, int], user_id: uuid.UUID
) -> dict[str, int]:
    existing = {p.kind: p for p in db.scalars(select(RetentionPolicy))}
    for kind, value in days.items():
        row = existing.get(kind)
        if row is None:
            db.add(RetentionPolicy(tenant_id=tenant_id, kind=kind, days=value, updated_by=user_id))
        else:
            row.days, row.updated_by = value, user_id
    db.flush()
    return policy(db)


def _cutoff(kind: str, confirmed: bool, pol: dict[str, int], now: datetime) -> datetime:
    return now - timedelta(days=pol["confirmed_case"] if confirmed else pol[kind])


def find_due(db: Session, now: datetime | None = None) -> tuple[list[Evidence], int]:
    """(evidence due for purging, number skipped because their alert is on legal hold)."""
    now = now or _now()
    pol = policy(db)
    rows = db.execute(
        select(Evidence, Alert)
        .outerjoin(Alert, Evidence.alert_id == Alert.id)
        .where(Evidence.purged_at.is_(None))
        .order_by(Evidence.created_at)
    ).all()
    due, held = [], 0
    for ev, alert in rows:
        confirmed = alert is not None and alert.status == AlertStatus.confirmed
        if ev.created_at >= _cutoff(ev.kind, confirmed, pol, now):
            continue
        if alert is not None and alert.legal_hold:
            held += 1
            continue
        due.append(ev)
    return due, held


def purge(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    dry_run: bool = True,
    actor_id: uuid.UUID | None = None,
    now: datetime | None = None,
    source: str = "api",
) -> PurgeReport:
    now = now or _now()
    due, held = find_due(db, now)
    rep = PurgeReport(dry_run=dry_run, candidates=len(due), held_skipped=held)
    for ev in due:
        rep.by_kind[ev.kind] = rep.by_kind.get(ev.kind, 0) + 1
        if dry_run:
            continue
        try:
            rep.files_removed += evidence_service.delete_files(ev)
        except Exception:
            rep.errors += 1
            continue
        ev.purged_at = now
        rep.purged += 1
        if len(rep.ids) < MAX_IDS_IN_AUDIT:
            rep.ids.append(str(ev.id))
    if not dry_run:
        db.commit()
    audit.record(
        tenant_id,
        AuditAction.retention_purged,
        actor_id=actor_id,
        resource_type="evidence",
        details={
            "dry_run": dry_run,
            "source": source,
            "candidates": rep.candidates,
            "purged": rep.purged,
            "held_skipped": rep.held_skipped,
            "errors": rep.errors,
            "by_kind": rep.by_kind,
            "ids": rep.ids,
            "policy": policy(db),
        },
    )
    return rep
