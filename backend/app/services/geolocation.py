"""Canonical location attribution. No visual inference, network lookup or media mutation."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.core.policy import Permission, can_view_alert, has_permission
from app.models import Alert, Camera, IncidentGeoSource, LocationRevision, Recording, Role
from app.services.geo_reference import classify

SUBJECTS = {
    "recording": (Recording, LocationRevision.recording_id),
    "alert": (Alert, LocationRevision.alert_id),
    "camera": (Camera, LocationRevision.camera_id),
}


def head(db, kind, subject_id, *, resolved=False):
    condition = SUBJECTS[kind][1] == subject_id
    q = select(LocationRevision).where(condition)
    if resolved:
        q = q.where(LocationRevision.state.in_(["confirmed", "unknown"]))
    return db.scalar(q.order_by(LocationRevision.revision.desc()).limit(1))


def subject(principal, kind, subject_id, *, lock=False):
    model = SUBJECTS[kind][0]
    stmt = select(model).where(model.id == subject_id)
    if lock:
        stmt = stmt.with_for_update()
    row = principal.db.scalar(stmt)
    if row is None or (kind == "alert" and not can_view_alert(principal, row)):
        raise HTTPException(404, "Source not found")
    if kind == "recording" and not has_permission(principal.role, Permission.videos_read):
        raise HTTPException(403, "Forbidden")
    return row


def out(row):
    if row is None:
        return None
    return dict(
        id=str(row.id),
        revision=row.revision,
        state=row.state,
        confidence=row.confidence,
        source_type=row.source_type,
        anchor_kind=row.anchor_kind,
        coordinates=[row.longitude, row.latitude] if row.latitude is not None else None,
        accuracy_m=row.accuracy_m,
        region=row.region,
        county_code=row.county_code,
        city_label=row.city_label,
        explanation=row.explanation,
        source_reference=row.source_reference,
        motion=row.motion,
        captured_at=row.captured_at,
        actor_id=str(row.actor_id),
        confirmed_at=row.created_at if row.state == "confirmed" else None,
        created_at=row.created_at,
        is_demo=row.is_demo,
        source_location_id=str(row.source_location_id) if row.source_location_id else None,
        config_revision=row.config_revision,
    )


def location_state(principal, kind, subject_id):
    row = subject(principal, kind, subject_id)
    current = head(principal.db, kind, subject_id)
    resolved = head(principal.db, kind, subject_id, resolved=True)
    return dict(
        revision=current.revision if current else 0,
        current=out(resolved),
        proposal=out(current) if current and current.state == "pending" else None,
        can_edit=has_permission(principal.role, Permission.location_edit),
        can_approve=principal.role == Role.tenant_admin,
    )


def assign(principal, kind, subject_id, body):
    if kind not in {"recording", "alert"}:
        raise HTTPException(422, "Camera locations use approved configuration revisions")
    row = subject(principal, kind, subject_id, lock=True)
    db = principal.db
    current = head(db, kind, subject_id)
    if (current.revision if current else 0) != body.expected_revision:
        raise HTTPException(409, "Location revision changed; reload before saving")
    if kind == "recording":
        locked = db.scalar(
            select(Alert.id)
            .join(IncidentGeoSource, IncidentGeoSource.alert_id == Alert.id)
            .where(
                IncidentGeoSource.recording_id == row.id,
                ((Alert.status == "confirmed") | Alert.legal_hold),
            )
            .limit(1)
        )
        if locked:
            raise HTTPException(
                409, "Reviewed/held incidents require independently approved incident correction"
            )
    if db.scalar(select(LocationRevision.id).where(LocationRevision.request_id == body.request_id)):
        raise HTTPException(409, "Location request already processed")
    point = body.point
    source = None
    state = body.state
    if body.source_location_id:
        source = db.get(LocationRevision, body.source_location_id)
        if source is None or source.camera_id is None or source.state != "confirmed":
            raise HTTPException(404, "Approved camera location not found")
        camera = db.get(Camera, source.camera_id)
        from app.models import CameraConfigVersion
        from app.services.camera_control import evaluate_eligibility, grants_for

        if (
            not camera
            or not camera.is_active
            or evaluate_eligibility(
                camera,
                grants_for(db, camera.id),
                db.get(CameraConfigVersion, source.config_version_id),
                datetime.now(UTC),
            )
        ):
            raise HTTPException(409, "Camera source permission is not active")
        if body.captured_at is None and not body.camera_valid_at_capture:
            raise HTTPException(
                422, "Unknown filming time requires explicit camera-position-at-capture attestation"
            )
        if body.captured_at:
            historical = db.scalar(
                select(LocationRevision)
                .where(
                    LocationRevision.camera_id == source.camera_id,
                    LocationRevision.created_at <= body.captured_at,
                    LocationRevision.state.in_(["confirmed", "unknown"]),
                )
                .order_by(LocationRevision.created_at.desc())
                .limit(1)
            )
            if historical is None or historical.id != source.id:
                raise HTTPException(
                    422, "Chosen camera position does not match the available capture-time history"
                )
    if kind == "alert":
        state = "pending"  # high-impact override always requires a different administrator
    lat = source.latitude if source else point.latitude if point else None
    lon = source.longitude if source else point.longitude if point else None
    region, county = classify(lat, lon) if lat is not None else ("unknown", None)
    location = LocationRevision(
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        revision=body.expected_revision + 1,
        request_id=body.request_id,
        state=state,
        confidence="operator_confirmed"
        if state == "confirmed"
        else "unverified"
        if state == "pending"
        else "unknown",
        source_type="registered_camera" if source else "manual_map_pin" if point else "unknown",
        anchor_kind="camera_position" if source else body.anchor_kind,
        latitude=lat,
        longitude=lon,
        accuracy_m=source.accuracy_m if source else body.accuracy_m,
        region=region,
        county_code=county,
        city_label=body.city_label,
        explanation=body.explanation,
        source_reference=body.source_reference,
        motion=body.motion,
        captured_at=body.captured_at,
        is_demo=body.is_demo
        or bool(current and current.is_demo)
        or bool(source and source.is_demo),
        source_location_id=source.id if source else None,
        config_revision=source.config_revision if source else None,
        **{kind + "_id": subject_id},
    )
    db.add(location)
    db.flush()
    db.commit()
    principal.audit(
        "location.proposed"
        if state == "pending"
        else "location.confirmed"
        if state == "confirmed"
        else "location.unknown",
        resource_type=kind,
        resource_id=subject_id,
        details=dict(
            location_revision_id=str(location.id),
            revision=location.revision,
            previous_revision=current.revision if current else 0,
            reason=body.explanation,
            source_type=location.source_type,
        ),
    )
    return location_state(principal, kind, subject_id)


def decide(principal, location_id, body):
    db = principal.db
    proposal = db.get(LocationRevision, location_id)
    if proposal is None or proposal.alert_id is None:
        raise HTTPException(404, "Proposal not found")
    subject(principal, "alert", proposal.alert_id, lock=True)
    current = head(db, "alert", proposal.alert_id)
    if (
        current.id != proposal.id
        or current.revision != body.expected_revision
        or current.state != "pending"
    ):
        raise HTTPException(409, "Proposal was superseded")
    if proposal.actor_id == principal.user_id:
        raise HTTPException(403, "A different administrator must review this location")
    copy = {
        c.name: getattr(proposal, c.name)
        for c in LocationRevision.__table__.columns
        if c.name
        not in {
            "id",
            "revision",
            "request_id",
            "created_at",
            "actor_id",
            "state",
            "confidence",
            "proposal_id",
        }
    }
    accepted = body.decision == "approve"
    next_row = LocationRevision(
        **copy,
        actor_id=principal.user_id,
        revision=current.revision + 1,
        state=("confirmed" if proposal.latitude is not None else "unknown")
        if accepted
        else "rejected",
        confidence="operator_confirmed" if accepted else "unverified",
        proposal_id=proposal.id,
    )
    db.add(next_row)
    db.flush()
    if accepted:
        from app.services.notifications import record as record_notification
        alert = db.get(Alert, proposal.alert_id)
        record_notification(db, alert, "location_revised", dedup_key=f"location:{next_row.id}")
    db.commit()
    principal.audit(
        "location.approved" if accepted else "location.rejected",
        resource_type="alerts",
        resource_id=proposal.alert_id,
        details=dict(
            proposal_id=str(proposal.id),
            location_revision_id=str(next_row.id),
            revision=next_row.revision,
            reason=body.reason,
        ),
    )
    return location_state(principal, "alert", proposal.alert_id)


def camera_activated(db, camera, version, actor_id):
    """Snapshot the exact reviewed config. Rollback reuses its immutable location, never edits history."""
    if db.scalar(
        select(LocationRevision.id).where(LocationRevision.config_version_id == version.id)
    ):
        return
    data = version.config.get("geolocation")
    current = head(db, "camera", camera.id)
    lat = data["latitude"] if data else None
    lon = data["longitude"] if data else None
    region, county = classify(lat, lon) if data else ("unknown", None)
    db.add(
        LocationRevision(
            tenant_id=camera.tenant_id,
            camera_id=camera.id,
            actor_id=actor_id,
            revision=current.revision + 1 if current else 1,
            state="confirmed" if data else "unknown",
            confidence="camera_registered" if data else "unknown",
            source_type="registered_camera",
            anchor_kind="camera_position",
            latitude=lat,
            longitude=lon,
            accuracy_m=data["accuracy_m"] if data else None,
            region=region,
            county_code=county,
            city_label=data.get("city_label") if data else None,
            explanation=data["explanation"]
            if data
            else "No geographic position in approved camera configuration",
            source_reference=data["source_reference"] if data else "unknown",
            motion="fixed",
            is_demo=bool(data and data.get("is_demo")),
            config_version_id=version.id,
            config_revision=version.revision,
        )
    )


def link_recording(db, alert, recording):
    db.add(
        IncidentGeoSource(tenant_id=alert.tenant_id, alert_id=alert.id, recording_id=recording.id)
    )


def link_camera(db, alert, camera, revision):
    # No fallback to mutable legacy coordinates or today's camera location.
    location = (
        db.scalar(
            select(LocationRevision).where(
                LocationRevision.camera_id == camera.id,
                LocationRevision.config_revision == revision,
            )
        )
        if isinstance(revision, int)
        else None
    )
    db.add(
        IncidentGeoSource(
            tenant_id=alert.tenant_id,
            alert_id=alert.id,
            camera_location_id=location.id if location else None,
        )
    )
