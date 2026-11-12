"""Archive navigation over real alerts: structured filters + the existing keyword parser,
stable keyset pagination and user-owned saved filters.

Sort (documented, stable): ``detected_at DESC, number DESC`` (number is unique per tenant, so
ties never reorder). The cursor is an opaque, HMAC-signed ``(detected_at, number)`` pair bound
to the caller's user id and to a digest of the filter, so a cursor from another user, another
tenant or another query is rejected with 400 instead of silently paging something else.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, exists, func, or_, select, tuple_

from app.config import get_settings
from app.models import Alert, AlertStatus, Camera, Evidence, Priority
from app.schemas.investigation import ArchiveFilters
from app.services import search as search_service

SORT = "detected_at_desc,number_desc"
MAX_PAGE = 100


class CursorError(ValueError):
    pass


def _key() -> bytes:
    return get_settings().url_signing_key.get_secret_value().encode()


def filter_digest(q: str | None, filters: ArchiveFilters) -> str:
    doc = {"q": (q or "").strip().lower(), "f": filters.model_dump(mode="json")}
    raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()[:32]


def _sig(user_id: uuid.UUID, digest: str, payload: str) -> str:
    msg = f"archive-cursor|{user_id}|{digest}|{payload}".encode()
    return hmac.new(_key(), msg, hashlib.sha256).hexdigest()[:32]


def encode_cursor(user_id: uuid.UUID, digest: str, detected_at: datetime, number: int) -> str:
    payload = f"1|{detected_at.astimezone(UTC).isoformat()}|{number}"
    body = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{body}.{_sig(user_id, digest, payload)}"


def decode_cursor(user_id: uuid.UUID, digest: str, cursor: str) -> tuple[datetime, int]:
    try:
        body, sig = cursor.split(".", 1)
        payload = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode()
    except (ValueError, UnicodeDecodeError) as exc:
        raise CursorError("malformed") from exc
    if not hmac.compare_digest(sig, _sig(user_id, digest, payload)):
        raise CursorError("signature")
    try:
        version, ts, number = payload.split("|")
        if version != "1":
            raise ValueError
        return datetime.fromisoformat(ts), int(number)
    except ValueError as exc:
        raise CursorError("malformed") from exc


def apply_filters(stmt: Select[Any], f: ArchiveFilters) -> Select[Any]:
    if f.camera_id:
        stmt = stmt.where(Camera.slug == f.camera_id)
    if f.types:
        stmt = stmt.where(Alert.event_type.in_(f.types))
    if f.exclude_types:
        stmt = stmt.where(Alert.event_type.not_in(f.exclude_types))
    if f.exclude_numbers:
        stmt = stmt.where(Alert.number.not_in(f.exclude_numbers))
    if f.statuses:
        stmt = stmt.where(Alert.status.in_([AlertStatus(x) for x in f.statuses]))
    if f.priorities:
        stmt = stmt.where(Alert.priority.in_([Priority(x) for x in f.priorities]))
    if f.date_from:
        stmt = stmt.where(Alert.detected_at >= f.date_from)
    if f.date_to:
        stmt = stmt.where(Alert.detected_at < f.date_to)
    if f.has_evidence is not None:
        has = exists().where(Evidence.alert_id == Alert.id, Evidence.purged_at.is_(None))
        stmt = stmt.where(has if f.has_evidence else ~has)
    if f.assigned_to == "unassigned":
        stmt = stmt.where(Alert.assigned_to.is_(None))
    elif f.assigned_to:
        stmt = stmt.where(Alert.assigned_to == uuid.UUID(f.assigned_to))
    if f.evidence_types:
        alert_kinds = [k for k in f.evidence_types if k != "camera_video"]
        conditions = []
        if alert_kinds:
            conditions.append(
                exists().where(
                    Evidence.alert_id == Alert.id,
                    Evidence.kind.in_(alert_kinds),
                    Evidence.purged_at.is_(None),
                )
            )
        if "camera_video" in f.evidence_types:
            # Annotated recordings belong to the camera, not to one alert.
            conditions.append(
                exists().where(
                    Evidence.camera_id == Alert.camera_id,
                    Evidence.alert_id.is_(None),
                    Evidence.kind == "camera_video",
                    Evidence.purged_at.is_(None),
                )
            )
        stmt = stmt.where(or_(*conditions))
    return stmt


EVIDENCE_TYPE_LABELS = {
    "keyframe": "cadru cheie",
    "clip": "clip video",
    "camera_video": "înregistrarea camerei",
}


def filter_chips(f: ArchiveFilters, names: dict[uuid.UUID, str]) -> list[dict[str, str]]:
    """How the server applied the newer structured filters, in words (Romanian)."""
    chips = []
    if f.assigned_to == "unassigned":
        chips.append({"key": "assigned_to", "label": "Responsabil: fără (neasignate)"})
    elif f.assigned_to:
        name = names.get(uuid.UUID(f.assigned_to), "utilizator necunoscut")
        chips.append({"key": "assigned_to", "label": f"Asignate lui: {name}"})
    if f.evidence_types:
        kinds = " sau ".join(EVIDENCE_TYPE_LABELS[k] for k in f.evidence_types)
        chips.append({"key": "evidence_types", "label": f"Cu probă stocată: {kinds}"})
    return chips


def run(
    db: Any,
    base: Any,
    *,
    user_id: uuid.UUID,
    q: str | None,
    filters: ArchiveFilters,
    cursor: str | None,
    limit: int,
) -> tuple[list[tuple[Alert, Camera]], str | None, int, dict[str, Any]]:
    """``base`` is already role-scoped. Returns (rows, next cursor, exact total, parsed)."""
    digest = filter_digest(q, filters)
    parsed: dict[str, Any] = {}
    stmt = base
    if q and q.strip():
        kw = search_service.parse_keywords(q)
        parsed = kw.model_dump()
        stmt = search_service.apply(stmt, kw)
    stmt = apply_filters(stmt, filters)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    if cursor:
        ts, number = decode_cursor(user_id, digest, cursor)
        stmt = stmt.where(tuple_(Alert.detected_at, Alert.number) < tuple_(ts, number))
    rows = list(
        db.execute(stmt.order_by(Alert.detected_at.desc(), Alert.number.desc()).limit(limit + 1))
    )
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1][0]
        next_cursor = encode_cursor(user_id, digest, last.detected_at, last.number)
    return [(a, c) for a, c in rows], next_cursor, total, parsed
