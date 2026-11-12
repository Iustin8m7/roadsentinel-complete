"""One RLS/role-filtered SQL projection over canonical alerts. No mutable marker index/cache."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import String, and_, case, cast, func, or_, select

from app.config import get_settings
from app.core.policy import Permission, has_permission, scope_alerts
from app.models import Alert, Camera, Evidence, IncidentGeoSource, LocationRevision, Recording
from app.services.geolocation import out


def _head(kind):
    col = getattr(LocationRevision, kind + "_id")
    ranked = (
        select(
            *LocationRevision.__table__.c,
            func.row_number()
            .over(partition_by=col, order_by=LocationRevision.revision.desc())
            .label("rank"),
        )
        .where(col.is_not(None), LocationRevision.state.in_(["confirmed", "unknown"]))
        .cte(kind + "_rank")
    )
    return (
        select(*[c for c in ranked.c if c.name != "rank"])
        .where(ranked.c.rank == 1)
        .cte(kind + "_geo")
    )


def projection(principal):
    record = _head("recording")
    override = _head("alert")
    anchor = LocationRevision.__table__.alias("camera_anchor")
    filming_location = LocationRevision.__table__.alias("filming_camera_location")
    filming_camera = Camera.__table__.alias("filming_camera")

    def resolved(name):
        return case(
            (override.c.id.is_not(None), override.c[name]),
            (record.c.id.is_not(None), record.c[name]),
            else_=anchor.c[name],
        )

    demo = or_(
        Alert.details["synthetic"].astext == "true",
        Alert.details["source"].astext == "app.services.seed",
        func.coalesce(resolved("is_demo"), False),
    )
    source = case(
        (
            Alert.details["origin"].astext.in_(["recorded_upload", "live_camera", "local_replay"]),
            Alert.details["origin"].astext,
        ),
        else_="unknown",
    )
    q = (
        select(
            Alert.id,
            Alert.number,
            Alert.event_type,
            cast(Alert.priority, String).label("severity"),
            cast(Alert.status, String).label("status"),
            Alert.detected_at,
            Alert.video_t,
            Alert.created_at,
            Alert.camera_id,
            Camera.slug.label("camera_slug"),
            Camera.name.label("camera_name"),
            source.label("source_kind"),
            IncidentGeoSource.recording_id,
            filming_camera.c.id.label("filming_camera_id"),
            filming_camera.c.name.label("filming_camera_name"),
            Recording.status.label("recording_status"),
            func.coalesce(demo, False).label("is_demo"),
            *[
                resolved(name).label(name)
                for name in (
                    "id",
                    "latitude",
                    "longitude",
                    "accuracy_m",
                    "confidence",
                    "source_type",
                    "anchor_kind",
                    "revision",
                    "region",
                    "county_code",
                    "city_label",
                    "captured_at",
                    "state",
                    "config_revision",
                )
                if name != "id"
            ],
            resolved("id").label("location_id"),
            select(Evidence.id)
            .where(Evidence.alert_id == Alert.id, Evidence.purged_at.is_(None))
            .exists()
            .label("has_evidence"),
        )
        .join(Camera, Camera.id == Alert.camera_id)
        .outerjoin(IncidentGeoSource, IncidentGeoSource.alert_id == Alert.id)
        .outerjoin(Recording, Recording.id == IncidentGeoSource.recording_id)
        .outerjoin(record, record.c.recording_id == IncidentGeoSource.recording_id)
        .outerjoin(filming_location, filming_location.c.id == record.c.source_location_id)
        .outerjoin(filming_camera, filming_camera.c.id == filming_location.c.camera_id)
        .outerjoin(override, override.c.alert_id == Alert.id)
        .outerjoin(anchor, anchor.c.id == IncidentGeoSource.camera_location_id)
    )
    return scope_alerts(q, principal).cte("visible_incidents")


def _cursor(body, principal, payload=None):
    query = body.model_dump(mode="json", exclude={"cursor"})
    digest = hashlib.sha256(json.dumps(query, sort_keys=True).encode()).hexdigest()
    binding = f"{principal.tenant_id}:{principal.user_id}:{principal.role}:{digest}"
    key = get_settings().url_signing_key.get_secret_value().encode()
    if payload is not None:
        raw = json.dumps(
            {**payload, "binding": binding, "expires": int(datetime.now(UTC).timestamp()) + 900},
            sort_keys=True,
        ).encode()
        token = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        sig = hmac.new(key, token.encode(), hashlib.sha256).hexdigest()
        return token + "." + sig
    if not body.cursor:
        return None
    try:
        token, sig = body.cursor.rsplit(".", 1)
        if not hmac.compare_digest(sig, hmac.new(key, token.encode(), hashlib.sha256).hexdigest()):
            raise ValueError()
        data = json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)))
        if data["binding"] != binding or data["expires"] < datetime.now(UTC).timestamp():
            raise ValueError()
        return data
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(422, "Invalid/expired map cursor") from None


def summary(row, principal):
    location = None
    if row["state"] == "confirmed" and row["latitude"] is not None:
        location = dict(
            id=str(row["location_id"]),
            coordinates=[row["longitude"], row["latitude"]],
            accuracy_m=row["accuracy_m"],
            confidence=row["confidence"],
            source_type=row["source_type"],
            anchor_kind=row["anchor_kind"],
            revision=row["revision"],
            region=row["region"],
            county_code=row["county_code"],
            city_label=row["city_label"],
            config_revision=row["config_revision"],
        )
    capture = row["captured_at"]
    occurred = (
        capture + timedelta(seconds=row["video_t"] or 0)
        if capture and row["source_kind"] == "recorded_upload"
        else None
    )
    return dict(
        id=str(row["id"]),
        number=row["number"],
        incident_type=row["event_type"],
        severity=row["severity"],
        status=row["status"],
        detected_at=row["detected_at"],
        occurred_at=occurred,
        timestamp_basis="operator_declared_capture" if occurred else "capture_time_unknown",
        video_t=row["video_t"],
        source=dict(
            kind=row["source_kind"],
            camera_id=str(row["camera_id"]),
            camera_slug=row["camera_slug"],
            camera_name=row["camera_name"],
            filming_camera_id=str(row["filming_camera_id"]) if row["filming_camera_id"] else None,
            filming_camera_name=row["filming_camera_name"],
            recording_id=str(row["recording_id"]) if row["recording_id"] else None,
        ),
        location=location,
        location_reason=None if location else "Locație neconfirmată; nu este dedusă din pixeli.",
        is_demo=row["is_demo"],
        can_view_evidence=bool(row["has_evidence"])
        and has_permission(principal.role, Permission.evidence_read),
        evidence_state="available" if row["has_evidence"] else "unavailable_or_expired",
        can_open_recording=has_permission(principal.role, Permission.videos_read)
        and bool(row["recording_id"])
        and row["recording_status"] == "ready",
        detail_href=f"/app/alerte/{row['number']}",
    )


def query(principal, body):
    if body.include_demo and not has_permission(principal.role, Permission.map_demo_read):
        raise HTTPException(403, "Demonstration layer is not permitted")
    v = projection(principal)
    c = v.c
    clauses = []
    if not body.include_demo:
        clauses.append(c.is_demo.is_(False))
    if body.statuses:
        clauses.append(c.status.in_(body.statuses))
    if body.types:
        clauses.append(c.event_type.in_(body.types))
    if body.severities:
        clauses.append(c.severity.in_(body.severities))
    for field in ("source_kind", "camera_id", "recording_id", "county_code", "city_label"):
        value = getattr(body, field)
        if value is not None:
            clauses.append(c[field] == value)
    if body.location_source:
        clauses.append(c.source_type == body.location_source)
    # Time filter is explicitly detection/system observation UTC, never invented capture time.
    if body.date_from:
        clauses.append(c.detected_at >= body.date_from)
    if body.date_to:
        clauses.append(c.detected_at <= body.date_to)
    located = and_(
        c.state == "confirmed",
        c.latitude.is_not(None),
        c.region.in_(["romania", "border_uncertain"]),
    )
    outside = and_(c.state == "confirmed", c.latitude.is_not(None), c.region == "outside")
    unknown = or_(c.state.is_(None), c.state != "confirmed", c.latitude.is_(None))
    if body.location_state == "located":
        clauses.append(located)
    elif body.location_state == "unknown":
        clauses.append(unknown)
    elif body.location_state == "outside":
        clauses.append(outside)
    base = select(v).where(*clauses).cte("filtered_map")
    # Rebind classifications to selected projection; all aggregates use the same tenant/role/filter set.
    b = base.c
    is_loc = and_(
        b.state == "confirmed",
        b.latitude.is_not(None),
        b.region.in_(["romania", "border_uncertain"]),
    )
    is_out = and_(b.state == "confirmed", b.latitude.is_not(None), b.region == "outside")
    counts = (
        principal.db.execute(
            select(
                func.count().label("total"),
                func.count().filter(is_loc).label("located"),
                func.count().filter(is_out).label("outside"),
            ).select_from(base)
        )
        .mappings()
        .one()
    )
    full = dict(counts)
    full["unknown"] = full["total"] - full["located"] - full["outside"]
    viewport = []
    if body.bbox:
        w, s, e, n = body.bbox
        viewport = [b.longitude.between(w, e), b.latitude.between(s, n)]
    points = select(base).where(is_loc, *viewport).cte("viewport_map")
    p = points.c
    # Adaptive cells bound national aggregation to <=~1200 groups; exact coincident events remain grouped.
    bounds = body.bbox or (20, 43, 30, 49)
    cell = max(360 / (2**body.zoom) / 4, (bounds[2] - bounds[0]) / 40, (bounds[3] - bounds[1]) / 30)
    gx, gy = func.floor(p.longitude / cell), func.floor(p.latitude / cell)
    groups = (
        principal.db.execute(
            select(
                gx.label("gx"),
                gy.label("gy"),
                func.count().label("count"),
                func.avg(p.longitude).label("longitude"),
                func.avg(p.latitude).label("latitude"),
                func.min(p.longitude).label("west"),
                func.max(p.longitude).label("east"),
                func.min(p.latitude).label("south"),
                func.max(p.latitude).label("north"),
            )
            .select_from(points)
            .group_by(gx, gy)
            .limit(1300)
        )
        .mappings()
        .all()
    )
    clusters = [
        dict(
            id=f"{row['gx']}:{row['gy']}",
            count=row["count"],
            coordinates=[float(row["longitude"]), float(row["latitude"])],
            bbox=[row["west"], row["south"], row["east"], row["north"]],
            anchor_kind="cluster_center",
        )
        for row in groups
    ]
    full["in_viewport"] = principal.db.scalar(select(func.count()).select_from(points))
    page = select(base)
    if body.bbox:
        page = page.where(or_(b.latitude.is_(None), and_(*viewport)))
    cursor = _cursor(body, principal)
    if cursor:
        at = datetime.fromisoformat(cursor["at"])
        id = cursor["id"]
        page = page.where(
            or_(b.detected_at < at, and_(b.detected_at == at, cast(b.id, String) < id))
        )
    result = (
        principal.db.execute(page.order_by(b.detected_at.desc(), b.id.desc()).limit(body.limit + 1))
        .mappings()
        .all()
    )
    next_cursor = (
        _cursor(
            body,
            principal,
            dict(
                at=result[body.limit - 1]["detected_at"].isoformat(),
                id=str(result[body.limit - 1]["id"]),
            ),
        )
        if len(result) > body.limit
        else None
    )
    return dict(
        items=[summary(row, principal) for row in result[: body.limit]],
        clusters=clusters,
        counts=full,
        next_cursor=next_cursor,
        count_scope="All authorized filtered incidents; in_viewport counts located points inside current bbox. List is paginated.",
        time_filter_basis="detected_at_utc",
        generated_at=datetime.now(UTC),
        refresh_after_seconds=8,
    )


def alert_location(db, alert):
    """Resolve the same precedence for a single case/export without exposing media URLs."""
    from app.services.geolocation import head

    value = head(db, "alert", alert.id, resolved=True)
    if value:
        return out(value)
    link = db.get(IncidentGeoSource, alert.id)
    if link is None:
        return None
    if link.recording_id:
        return out(head(db, "recording", link.recording_id, resolved=True))
    return (
        out(db.get(LocationRevision, link.camera_location_id)) if link.camera_location_id else None
    )
