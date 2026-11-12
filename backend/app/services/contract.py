"""Read side of the API.md contract on top of the secure data model.

Everything here runs inside a tenant-bound session (RLS), so a query can only ever see the
caller's tenant. Public ids are per-tenant (alert ``number``, camera ``slug``, audit ``seq``).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from sqlalchemy import Select, case, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.audit import AuditAction
from app.core.crypto import sign_url_params, verify_url_params
from app.models import PRIORITY_ORDER, Alert, AlertStatus, AuditLog, Camera, Evidence, User
from app.schemas.contract import AuditEntry, Event

MEDIA_PURPOSE = "media"
VARIANT = "redacted"  # the contract only ever links the redacted variant

# Chain action -> contract action (others are security events, not shown in the contract).
AUDIT_ACTIONS: dict[str, str] = {
    AuditAction.login_success.value: "login",
    AuditAction.alert_created.value: "detected",
    AuditAction.alert_viewed.value: "viewed",
    AuditAction.alert_confirmed.value: "confirmed",
    AuditAction.alert_rejected.value: "rejected",
}
VLM_ACTIONS = {"confirmed": "vlm_confirmed", "rejected": "vlm_rejected"}


# --------------------------------------------------------------------------- media URLs


def _key() -> bytes:
    return get_settings().url_signing_key.get_secret_value().encode()


def media_url(user_id: uuid.UUID, evidence_id: uuid.UUID) -> str:
    """Signed, user-bound media URL. The session cookie is checked on every request too; the
    signature only stops a link from working in another account."""
    exp = int(time.time()) + get_settings().media_view_ttl_seconds
    sig = sign_url_params(_key(), MEDIA_PURPOSE, f"{evidence_id}:{VARIANT}", str(user_id), exp)
    return f"/api/media/{evidence_id}?{urlencode({'exp': exp, 'sig': sig})}"


def media_signature_ok(user_id: uuid.UUID, evidence_id: uuid.UUID, exp: int, sig: str) -> bool:
    return verify_url_params(
        _key(), MEDIA_PURPOSE, f"{evidence_id}:{VARIANT}", str(user_id), exp, sig
    )


# --------------------------------------------------------------------------- events


def local_time(alert: Alert, camera: Camera) -> datetime:
    """Contract times are naive local camera time."""
    return alert.detected_at.astimezone(ZoneInfo(camera.timezone)).replace(tzinfo=None)


def visible_alerts() -> Select[Alert, Camera]:
    """Alerts shown through the contract: pipeline alerts that were not superseded."""
    return (
        select(Alert, Camera)
        .join(Camera, Camera.id == Alert.camera_id)
        .where(Alert.superseded_at.is_(None))
    )


_PRIORITY_RANK = case(dict(PRIORITY_ORDER), value=Alert.priority)


def queue_order(stmt: Select[Alert, Camera]) -> Select[Alert, Camera]:
    """API.md order, applied in SQL before any LIMIT: undecided first, then priority
    (critical first), then oldest first."""
    return stmt.order_by(Alert.status != AlertStatus.new, _PRIORITY_RANK, Alert.detected_at)


def _evidence_by_alert(db: Session, alert_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, dict]:
    out: dict[uuid.UUID, dict[str, Evidence]] = {}
    if not alert_ids:
        return out
    rows = db.scalars(
        select(Evidence).where(Evidence.alert_id.in_(alert_ids)).order_by(Evidence.created_at)
    )
    for ev in rows:
        if ev.alert_id is not None:
            out.setdefault(ev.alert_id, {})[ev.kind] = ev
    return out


def _redaction(*files: Evidence | None) -> str | None:
    return next((f.redaction for f in files if f is not None), None)


def to_events(db: Session, user_id: uuid.UUID, rows: Iterable[tuple[Alert, Camera]]) -> list[Event]:
    rows = list(rows)
    evidence = _evidence_by_alert(db, [a.id for a, _ in rows])
    out = []
    for alert, camera in rows:
        files = evidence.get(alert.id, {})
        keyframe, clip = files.get("keyframe"), files.get("clip")
        out.append(
            Event(
                id=alert.number,
                camera_id=camera.slug,
                camera_name=camera.name,
                location=camera.location,
                type=alert.event_type,
                priority=alert.priority.value,
                occurred_at=local_time(alert, camera),
                video_t=alert.video_t or 0.0,
                track_id=alert.track_id,
                object_class=alert.object_class,
                speed_kmh=alert.speed_kmh,
                rule=alert.rule or alert.description,
                details=alert.details or {},
                keyframe_url=(
                    media_url(user_id, keyframe.id) if keyframe and not keyframe.purged_at else None
                ),
                clip_url=media_url(user_id, clip.id) if clip and not clip.purged_at else None,
                evidence_purged=any(
                    f.purged_at is not None for f in (keyframe, clip) if f is not None
                ),
                vlm_status=alert.vlm_status,  # type: ignore[arg-type]
                vlm_text=alert.vlm_text,
                status=alert.status.value,
                action=alert.action,
                redaction=_redaction(keyframe, clip),
                has_original=any(f.has_original for f in (keyframe, clip) if f is not None),
            )
        )
    return out


def camera_video(db: Session, camera_id: uuid.UUID) -> Evidence | None:
    return db.scalar(
        select(Evidence)
        .where(Evidence.camera_id == camera_id, Evidence.kind == "camera_video")
        .order_by(Evidence.created_at.desc())
        .limit(1)
    )


# --------------------------------------------------------------------------- audit


def _contract_action(entry: AuditLog) -> str | None:
    if entry.action == AuditAction.alert_vlm_verdict.value:
        return VLM_ACTIONS.get(str(entry.details.get("verdict")), "vlm_uncertain")
    return AUDIT_ACTIONS.get(entry.action)


def audit_query() -> Select[AuditLog]:
    return select(AuditLog).where(
        AuditLog.action.in_([*AUDIT_ACTIONS, AuditAction.alert_vlm_verdict.value])
    )


def to_audit(db: Session, entries: Sequence[AuditLog]) -> list[AuditEntry]:
    """Map chain entries to the contract shape. Actors are resolved from the user table (never
    from anything a client sent); detections are "system", VLM verdicts "vlm:<model>"."""
    user_ids = {e.actor_id for e in entries if e.actor_id}
    names = (
        dict(db.execute(select(User.id, User.display_name).where(User.id.in_(user_ids))).all())
        if user_ids
        else {}
    )
    alert_ids = {
        uuid.UUID(e.resource_id) for e in entries if e.resource_type == "alerts" and e.resource_id
    }
    alerts = (
        dict(db.execute(select(Alert.id, Alert.number).where(Alert.id.in_(alert_ids))).all())
        if alert_ids
        else {}
    )
    types = (
        dict(db.execute(select(Alert.id, Alert.event_type).where(Alert.id.in_(alert_ids))).all())
        if alert_ids
        else {}
    )
    out = []
    for e in entries:
        action = _contract_action(e)
        if action is None:
            continue
        alert_id = (
            uuid.UUID(e.resource_id) if e.resource_type == "alerts" and e.resource_id else None
        )
        if e.action == AuditAction.alert_vlm_verdict.value:
            actor = f"vlm:{e.details.get('model', 'unknown')}"
        elif e.actor_id:
            actor = names.get(e.actor_id, "utilizator")
        else:
            actor = "system"
        out.append(
            AuditEntry(
                id=e.seq,
                event_id=alerts.get(alert_id) if alert_id else None,
                actor=actor,
                action=action,
                note=(e.details.get("note") or e.details.get("rule") or None),
                at=e.ts.astimezone(UTC),
                type=types.get(alert_id) if alert_id else None,
            )
        )
    return out


def audit_for_alert(db: Session, alert: Alert) -> list[AuditEntry]:
    entries = db.scalars(
        audit_query()
        .where(AuditLog.resource_type == "alerts", AuditLog.resource_id == str(alert.id))
        .order_by(AuditLog.seq)
    ).all()
    return to_audit(db, entries)
