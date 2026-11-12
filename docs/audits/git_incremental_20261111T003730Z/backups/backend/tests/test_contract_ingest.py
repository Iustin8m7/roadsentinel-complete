"""API.md ingestion on the secure backend: signed multipart events, camera videos, resets."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.db import tenant_session
from app.models import Alert, Camera, Evidence
from tests.conftest import World, admin_conn, audit_actions
from tests.test_ingest_auth import Pipeline, make_pipeline

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 400

EVENT: dict[str, Any] = {
    "camera_id": "demo-highway",
    "camera_name": "ignored",
    "location": "ignored",
    "type": "very_high_speed",
    "occurred_at": "2026-10-16T14:05:16",
    "video_t": 16.5,
    "track_id": 72,
    "object_class": "car",
    "speed_kmh": 155.0,
    "rule": "Viteză 155 km/h > prag 150 km/h (limită 130)",
    "details": {"limit_kmh": 130, "measured_kmh": 155.0},
    "vlm_status": "skipped",
    "vlm_text": None,
}


def add_camera(tenant_id: uuid.UUID, slug: str, name: str = "Autostradă demo") -> uuid.UUID:
    with tenant_session(tenant_id) as db:
        cam = Camera(tenant_id=tenant_id, slug=slug, name=name, location="km 12")
        db.add(cam)
        db.commit()
        return cam.id


def send(
    pipe: Pipeline,
    method: str,
    target: str,
    *,
    data: dict[str, str] | None = None,
    files: dict[str, tuple[str, bytes, str]] | None = None,
) -> Any:
    """Sign the exact multipart bytes, as roadsentinel/sink.py does."""
    req = httpx.Request(method, f"https://testserver{target}", data=data, files=files)
    body = req.read()
    headers = pipe.headers(method, target, body)
    if "content-type" in req.headers:
        headers["Content-Type"] = req.headers["content-type"]
    return pipe.http.request(method, target, content=body, headers=headers)


def post_event(
    pipe: Pipeline, event: dict[str, Any] | str = EVENT, keyframe: bytes = JPEG, clip: bytes = MP4
) -> Any:
    raw = event if isinstance(event, str) else json.dumps(event)
    return send(
        pipe,
        "POST",
        "/api/ingest/events",
        data={"event": raw},
        files={"keyframe": ("k.jpg", keyframe, "image/jpeg"), "clip": ("c.mp4", clip, "video/mp4")},
    )


@pytest.fixture
def highway(world: World) -> uuid.UUID:
    return add_camera(world.a.id, "demo-highway")


@pytest.fixture
def pipe(world: World, highway: uuid.UUID) -> Pipeline:
    return make_pipeline(world.a.id)[0]


def alerts_of(tenant_id: uuid.UUID) -> list[Alert]:
    with tenant_session(tenant_id) as db:
        return list(db.query(Alert).filter(Alert.rule.is_not(None)).order_by(Alert.number))


class TestIngestEvent:
    def test_stores_alert_and_encrypted_evidence(self, world: World, pipe: Pipeline) -> None:
        r = post_event(pipe)
        assert r.status_code == 200, r.text
        number = r.json()["id"]
        [alert] = alerts_of(world.a.id)
        assert alert.number == number
        assert alert.priority.value == "high"  # derived from the type
        assert alert.speed_kmh == 155.0 and alert.track_id == 72
        # Naive local time (Europe/Bucharest, UTC+3 in October) is stored as UTC.
        assert alert.detected_at.astimezone(UTC) == datetime(2026, 10, 16, 11, 5, 16, tzinfo=UTC)
        with tenant_session(world.a.id) as db:
            evidence = db.query(Evidence).filter(Evidence.alert_id == alert.id).all()
        assert {e.kind for e in evidence} == {"keyframe", "clip"}
        assert {e.redaction for e in evidence} == {"unknown"}
        assert {e.has_original for e in evidence} == {False}
        assert "alert.created" in audit_actions(world.a.id)

    def test_numbers_are_per_tenant_and_monotonic(self, world: World, pipe: Pipeline) -> None:
        first = post_event(pipe).json()["id"]
        second = post_event(pipe).json()["id"]
        assert second == first + 1
        add_camera(world.b.id, "demo-highway")
        b_pipe, _ = make_pipeline(world.b.id, "pipe-b")
        # Unit B's fixture alerts are numbered 1..3 independently of Unit A.
        assert post_event(b_pipe).json()["id"] == 4

    @pytest.mark.parametrize(
        "patch",
        [
            pytest.param({"type": "ufo"}, id="unknown-type"),
            pytest.param({"priority": "critical"}, id="priority-not-accepted"),
            pytest.param({"camera_id": "../x"}, id="path-traversal"),
            pytest.param({"camera_id": "nope"}, id="unknown-camera"),
            pytest.param({"occurred_at": "2026-10-16T14:05:16+02:00"}, id="offset-time"),
            pytest.param({"speed_kmh": 9999}, id="speed-out-of-range"),
            pytest.param({"rule": ""}, id="empty-rule"),
            pytest.param({"details": {"a": "x" * 5000}}, id="details-too-big"),
            pytest.param({"details": {"a": {"b": {"c": {"d": 1}}}}}, id="details-too-deep"),
        ],
    )
    def test_invalid_event_is_rejected_and_nothing_stored(
        self, world: World, pipe: Pipeline, patch: dict[str, Any]
    ) -> None:
        r = post_event(pipe, {**EVENT, **patch})
        assert r.status_code == 422, r.text
        assert alerts_of(world.a.id) == []

    @pytest.mark.parametrize(
        ("keyframe", "clip"),
        [(b"not a jpeg", MP4), (JPEG, b"not an mp4 at all"), (JPEG, JPEG)],
        ids=["bad-keyframe", "bad-clip", "jpeg-as-clip"],
    )
    def test_media_types_are_checked(
        self, world: World, pipe: Pipeline, keyframe: bytes, clip: bytes
    ) -> None:
        assert post_event(pipe, keyframe=keyframe, clip=clip).status_code == 422
        assert alerts_of(world.a.id) == []

    def test_bad_json(self, world: World, pipe: Pipeline) -> None:
        assert post_event(pipe, "{nope").status_code == 422

    def test_unsigned_request_is_refused(self, world: World, pipe: Pipeline) -> None:
        r = pipe.http.post("/api/ingest/events", data={"event": json.dumps(EVENT)})
        assert r.status_code == 401
        assert alerts_of(world.a.id) == []

    def test_camera_scope_is_enforced(self, world: World, highway: uuid.UUID) -> None:
        other = add_camera(world.a.id, "demo-urban")
        scoped, _ = make_pipeline(world.a.id, "urban-only", camera_ids=[other])
        assert post_event(scoped).status_code == 403
        assert post_event(scoped, {**EVENT, "camera_id": "demo-urban"}).status_code == 200

    def test_other_tenants_camera_is_unknown(self, world: World, pipe: Pipeline) -> None:
        add_camera(world.b.id, "only-in-b")
        assert post_event(pipe, {**EVENT, "camera_id": "only-in-b"}).status_code == 422

    def test_vlm_verdict_is_audited_with_provider(self, world: World, pipe: Pipeline) -> None:
        event = {
            **EVENT,
            "vlm_status": "confirmed",
            "vlm_text": "Autoturism care depășește coloana.",
            "details": {"vlm": {"verdict": "confirmed", "reason": "clear view"}},
        }
        assert post_event(pipe, event).status_code == 200
        with admin_conn() as conn:
            row = conn.execute(
                "SELECT details FROM audit_log WHERE tenant_id = %s AND action = %s",
                (world.a.id, "alert.vlm_verdict"),
            ).fetchone()
        assert row is not None
        assert row[0]["model"] == "claude-opus-5-5" and row[0]["verdict"] == "confirmed"


class TestCameraVideoAndReset:
    def test_camera_video_is_stored_as_camera_evidence(
        self, world: World, pipe: Pipeline, highway: uuid.UUID
    ) -> None:
        r = send(
            pipe,
            "PUT",
            "/api/ingest/cameras/demo-highway/video",
            files={"video": ("annotated.mp4", MP4, "video/mp4")},
        )
        assert r.status_code == 204, r.text
        with tenant_session(world.a.id) as db:
            [ev] = db.query(Evidence).filter(Evidence.camera_id == highway).all()
        assert ev.kind == "camera_video" and ev.alert_id is None

    def test_reset_hides_undecided_alerts_and_deletes_nothing(
        self, world: World, pipe: Pipeline
    ) -> None:
        post_event(pipe)
        r = send(pipe, "DELETE", "/api/ingest/cameras/demo-highway")
        assert r.status_code == 204, r.text
        [alert] = alerts_of(world.a.id)
        assert alert.superseded_at is not None
        assert "ingest.camera_superseded" in audit_actions(world.a.id)

    def test_reset_is_refused_in_production(
        self, world: World, pipe: Pipeline, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.config import get_settings

        post_event(pipe)
        monkeypatch.setattr(type(get_settings()), "is_production", property(lambda s: True))
        r = send(pipe, "DELETE", "/api/ingest/cameras/demo-highway")
        assert r.status_code == 403
        assert alerts_of(world.a.id)[0].superseded_at is None
        assert "ingest.camera_clear_denied" in audit_actions(world.a.id)


def test_register_camera_cli_is_idempotent(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    from app.cli import main

    args = ["register-camera", "--tenant", "unit-a", "--slug", "demo-urban"]
    main([*args, "--name", "Pasaj", "--location", "km 1"])
    main([*args, "--name", "Pasaj subteran", "--location", "km 2"])
    out = capsys.readouterr().out
    assert "created camera demo-urban" in out and "updated camera demo-urban" in out
    with tenant_session(world.a.id) as db:
        [cam] = db.query(Camera).filter(Camera.slug == "demo-urban").all()
    assert cam.name == "Pasaj subteran"


class TestHeartbeat:
    def last_seen(self, tenant_id: uuid.UUID, camera_id: uuid.UUID) -> datetime | None:
        with tenant_session(tenant_id) as db:
            cam = db.get(Camera, camera_id)
            assert cam is not None
            return cam.last_seen_at

    def test_heartbeat_marks_the_camera_as_seen(
        self, world: World, pipe: Pipeline, highway: uuid.UUID
    ) -> None:
        assert self.last_seen(world.a.id, highway) is None
        r = send(pipe, "POST", "/api/ingest/cameras/demo-highway/heartbeat")
        assert r.status_code == 204, r.text
        seen = self.last_seen(world.a.id, highway)
        assert seen is not None and (datetime.now(UTC) - seen).total_seconds() < 60

    def test_heartbeat_for_an_unknown_camera_is_rejected(self, pipe: Pipeline) -> None:
        r = send(pipe, "POST", "/api/ingest/cameras/no-such-cam/heartbeat")
        assert r.status_code == 422

    def test_an_ingested_event_also_marks_the_camera_as_seen(
        self, world: World, pipe: Pipeline, highway: uuid.UUID
    ) -> None:
        assert post_event(pipe).status_code == 200
        assert self.last_seen(world.a.id, highway) is not None
