from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.db import tenant_session
from app.models import Recording, Role


def test_recording_routes_require_video_permissions_and_hide_other_tenants(
    client, login, world
) -> None:
    assert client.get("/api/recordings").status_code == 401
    operator = login(world.a.operator)
    assert operator.get("/api/recordings").status_code == 200

    assert login(world.a.patrol).get("/api/recordings").status_code == 403

    recording_id = uuid.uuid4()
    with tenant_session(world.a.id) as db:
        db.add(
            Recording(
                id=recording_id,
                tenant_id=world.a.id,
                owner_user_id=world.a.users[Role.operator].id,
                original_filename="private.webm",
                storage_key=f"offline-analysis/{world.a.id}/{recording_id}/source.rse",
                sha256="a" * 64,
                size_bytes=1,
                codec="vp8",
                duration_ms=1000,
                width=320,
                height=240,
                fps_num=1,
                fps_den=1,
                imported_at=datetime.now(UTC),
                status="ready",
                crop={"x": 0, "y": 0, "width": 1, "height": 1, "confirmed": False},
            )
        )
        db.commit()

    assert login(world.b.operator).get(f"/api/recordings/{recording_id}").status_code == 404
    rights = {
        "source_name": "Licensed test recording",
        "rightsholder": "Fixture rightsholder",
        "permission_basis": "licensed",
        "authorization_reference": "Local fixture license record",
        "scope": "Offline detection, evidence extraction and retention for tests",
        "allow_analysis": True,
        "allow_evidence_extraction": True,
        "allow_retention": True,
        "operator_declaration": True,
    }
    path = f"/api/recordings/{recording_id}/rights"
    blocked = operator.post(f"/api/recordings/{recording_id}/analyses", json={"crop_revision": 1})
    assert blocked.status_code == 409 and "source rights" in blocked.json()["detail"]
    assert login(world.b.operator).patch(path, json={"expected_revision": 0, "rights": rights}).status_code == 404
    assert login(world.a.patrol).patch(path, json={"expected_revision": 0, "rights": rights}).status_code == 403
    assert operator.patch(path, json={"expected_revision": 0, "rights": rights}).status_code == 200
    blocked = operator.post(f"/api/recordings/{recording_id}/analyses", json={"crop_revision": 1})
    assert blocked.status_code == 409 and "location" in blocked.json()["detail"]
    assert operator.patch(path, json={"expected_revision": 0, "rights": rights}).status_code == 409
    expired = {**rights, "expires_at": (datetime.now(UTC)-timedelta(seconds=1)).isoformat()}
    assert operator.patch(path, json={"expected_revision": 1, "rights": expired}).status_code == 422
    persisted = operator.get(f"/api/recordings/{recording_id}").json()
    assert persisted["rights_revision"] == 1
    assert persisted["rights_context"]["permission_basis"] == "licensed"
