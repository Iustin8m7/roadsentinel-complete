from __future__ import annotations

import uuid
from datetime import UTC, datetime

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
