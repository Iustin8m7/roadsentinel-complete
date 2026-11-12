"""Pinned GitHub editor/catalogue and protected recording-range regressions."""

import pytest

from app.db import tenant_session
from app.models import Camera
from app.services import camera_config as cc
from app.services.http_range import bounds, slice_stream


def test_editor_catalogue_matches_authoritative_validator(client, login, world):
    assert client.get("/api/camera-control/catalog").status_code == 401
    result = login(world.a.admin).get("/api/camera-control/catalog")
    assert result.status_code == 200
    catalog = result.json()
    assert {r["id"] for r in catalog["rules"]} == set(cc.RULES)
    assert {r["id"] for r in catalog["thresholds"] if r["required"]} == set(cc.REQUIRED_THRESHOLDS)
    assert catalog["coordinate_convention"] == "pixels_top_left"
    # Auditors may inspect the non-tenant rule catalogue, but may not mutate cameras.
    assert login(world.a.auditor).get("/api/camera-control/catalog").status_code == 200


def test_managed_ui_creation_is_not_runnable_and_duplicate_is_conflict(login, world):
    admin = login(world.a.admin)
    data = {
        "name": "LOCAL RECORDED REPLAY",
        "location": "Licensed test",
        "slug": "ui-managed",
        "managed": True,
    }
    response = admin.post("/api/cameras", data)
    assert response.status_code == 201
    import uuid

    with tenant_session(world.a.id) as db:
        camera = db.get(Camera, uuid.UUID(response.json()["id"]))
        assert camera.lifecycle_state == "onboarding" and not camera.desired_enabled
    assert admin.post("/api/cameras", data).status_code == 409
    assert login(world.a.operator).post("/api/cameras", data).status_code == 403
    foreign = login(world.b.admin).get(f"/api/camera-control/cameras/{response.json()['id']}")
    assert foreign.status_code == 404


@pytest.mark.parametrize(
    "value,expected",
    [
        ("bytes=0-3", (0, 3)),
        ("bytes=3-", (3, 9)),
        ("bytes=-3", (7, 9)),
        ("bytes=5-100", (5, 9)),
        ("bytes=-100", (0, 9)),
    ],
)
def test_single_range_bounds(value, expected):
    assert bounds(value, 10) == expected
    assert (
        b"".join(slice_stream(iter([b"012", b"3456", b"789"]), *expected))
        == b"0123456789"[expected[0] : expected[1] + 1]
    )


@pytest.mark.parametrize(
    "value", ["bytes=", "bytes=9-2", "bytes=10-", "bytes=-0", "bytes=0-1,3-4", "items=0-2"]
)
def test_invalid_ranges_fail_closed(value):
    with pytest.raises(ValueError):
        bounds(value, 10)


def test_signed_media_ranges_still_enforce_identity_and_tenant(login, world):
    owner = login(world.a.operator)
    event = next(row for row in owner.get("/api/events").json() if row["keyframe_url"])
    url = event["keyframe_url"]
    whole = owner.get(url)
    part = owner.get(url, headers={"Range": "bytes=1-12"})
    assert part.status_code == 206 and part.content == whole.content[1:13]
    assert part.headers["content-length"] == "12"
    assert part.headers["content-range"] == f"bytes 1-12/{len(whole.content)}"
    assert "no-store" in part.headers["cache-control"]
    assert owner.get(url, headers={"Range": "bytes=999999-"}).status_code == 416
    assert login(world.b.operator).get(url, headers={"Range": "bytes=0-1"}).status_code in (
        403,
        404,
    )
