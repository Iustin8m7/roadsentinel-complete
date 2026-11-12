"""Camera control plane (workstream A): config schema, eligibility, version lifecycle,
four-eyes, activation races, worker handshake, status truthfulness and secret handling.

Acceptance ids (A01..A20) are referenced in the test names/docstrings."""

from __future__ import annotations

import copy
import json
import logging
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import pytest

from app.models import Camera, CameraConfigVersion, CameraSourceGrant, Role
from app.services import camera_config as cc
from app.services import camera_control as ctl
from app.services.camera_control import ControlError
from tests.conftest import (
    ApiClient,
    World,
    admin_conn,
    app_conn,
    audit_actions,
    make_user,
)
from tests.test_contract_ingest import JPEG, MP4, send
from tests.test_ingest_auth import Pipeline, make_pipeline

FIXTURES = Path(__file__).parent / "fixtures" / "camera_config"
VALID: dict[str, Any] = json.loads((FIXTURES / "valid_demo_urban.json").read_text())["config"]
INVALID = json.loads((FIXTURES / "invalid_geometry_and_rules.json").read_text())
BASE = "/api/camera-control/cameras"
SECRET_URL = "rtsps://viewer:S3cr3tPass@cam.example.org:8554/live/ch1?token=TOPSECRET42"
SECRET_MARKERS = ("S3cr3tPass", "TOPSECRET42", "viewer:", "/live/ch1")


def config(**overrides: Any) -> dict[str, Any]:
    out = copy.deepcopy(VALID)
    out.update(overrides)
    return out


def grant_body(**overrides: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    body = {
        "granting_party": "Owner of the local test recording",
        "basis": "own_infrastructure",
        "basis_reference": "TEST-REF-001",
        "purpose": "Integration test of the control plane",
        "valid_from": (now - timedelta(days=1)).isoformat(),
        "valid_until": (now + timedelta(days=30)).isoformat(),
        "capture_method": "recorded_replay",
        "max_analysis_fps": 30,
        "max_frame_height": 1080,
        "retention_days": 30,
        "export_allowed": False,
        "media_scope": "events_only",
    }
    body.update(overrides)
    return body


# --------------------------------------------------------------------------- unit: schema


class TestConfigSchema:
    def test_valid_fixture_has_no_errors(self) -> None:
        assert cc.validate(VALID) == []
        # The pipeline (roadsentinel/remote_config.py) asserts the same value: one algorithm.
        expected = json.loads((FIXTURES / "valid_demo_urban.json").read_text())
        assert cc.fingerprint(VALID) == expected["expected_fingerprint"]

    def test_invalid_fixture_errors_are_precise_and_complete(self) -> None:
        """A06: every malformed geometry/rule setting gets a field-addressed error."""
        got = {(e.path, e.code) for e in cc.validate(INVALID["config"])}
        expected = {(e["path"], e["code"]) for e in INVALID["expected_errors"]}
        assert got == expected

    @pytest.mark.parametrize(
        ("mutate", "path", "code"),
        [
            (
                lambda c: c.update(rules=["hard_braking"]) or c["acquisition"].update(target_fps=5),
                "rules[0]",
                "unsupported_at_fps",
            ),
            (lambda c: c["zones"][0].pop("direction"), "zones[0].direction", "required"),
            (lambda c: c.update(rules=["stopped_emergency_lane"]), "rules[0]", "zone_required"),
            (
                lambda c: c["calibration"].update(source=[[0, 0], [1, 1], [2, 2], [3, 3]]),
                "calibration.source",
                "degenerate_calibration",
            ),
            (
                lambda c: c["thresholds"].pop("stopped_seconds"),
                "thresholds.stopped_seconds",
                "required",
            ),
            (
                lambda c: c["thresholds"].update(congestion_vehicles=6.5),
                "thresholds.congestion_vehicles",
                "invalid_type",
            ),
            (
                lambda c: c["reference_frame"].update(coordinate_convention="center"),
                "reference_frame.coordinate_convention",
                "unsupported_value",
            ),
            (lambda c: c["model"].update(id="../../etc/passwd"), "model.id", "invalid_id"),
            (
                lambda c: c["zones"][0].update(polygon=[[0, 0], [100, 0], [200, 0]]),
                "zones[0].polygon",
                "degenerate_polygon",
            ),
            (lambda c: c.update(schema_version=2), "schema_version", "unsupported_schema"),
        ],
    )
    def test_targeted_errors(self, mutate: Any, path: str, code: str) -> None:
        c = config()
        mutate(c)
        assert (path, code) in {(e.path, e.code) for e in cc.validate(c)}

    def test_never_raises_on_garbage(self) -> None:
        for junk in (None, [], "x", 1, {"zones": "x", "rules": 5, "thresholds": []}):
            assert cc.validate(junk)

    def test_pedestrian_rule_alone_needs_no_calibration(self) -> None:
        c = config(calibration=None, rules=["pedestrian_on_road"])
        assert cc.validate(c) == []

    def test_fingerprint_is_canonical(self) -> None:
        a = config()
        b = json.loads(json.dumps(a))
        b["rules"] = list(reversed(b["rules"]))
        b["acquisition"]["target_fps"] = 25.0
        b = dict(reversed(list(b.items())))
        assert cc.fingerprint(a) == cc.fingerprint(b)
        assert cc.fingerprint(a) != cc.fingerprint(config(min_y=621))
        # Zone order is semantic (first zone containing a point wins) and is kept.
        c = config()
        c["zones"] = list(reversed(c["zones"]))
        assert cc.fingerprint(a) != cc.fingerprint(c)

    def test_diff_is_stable_and_keyed_by_zone_id(self) -> None:
        after = config()
        after["thresholds"]["congestion_vehicles"] = 8
        after["zones"][1]["polygon"][0] = [721, 600]
        changes = cc.diff(VALID, after)
        assert [c["path"] for c in changes] == [
            "thresholds.congestion_vehicles",
            "zones[id=carriageway_toward].polygon",
        ]
        assert changes == cc.diff(json.loads(json.dumps(VALID)), after)
        assert cc.diff(VALID, VALID) == []
        assert all(c["op"] == "added" for c in cc.diff(None, VALID))


# --------------------------------------------------------------------------- unit: sources


class TestSources:
    @pytest.mark.parametrize(
        ("kind", "url", "display", "creds"),
        [
            (
                "recorded_replay",
                "replay://data/videos/vehicles-2.mp4",
                "replay://data/videos/vehicles-2.mp4",
                False,
            ),
            ("authorized_network_live", SECRET_URL, "rtsps://cam.example.org:8554", True),
            (
                "authorized_network_live",
                "https://hls.example.org/x/index.m3u8",
                "https://hls.example.org",
                False,
            ),
            ("owned_optical_live", "device://0", "device://0", False),
        ],
    )
    def test_accepted_and_sanitized(self, kind: str, url: str, display: str, creds: bool) -> None:
        parsed = ctl.parse_source(kind, url)
        assert (parsed.display, parsed.has_credentials) == (display, creds)

    @pytest.mark.parametrize(
        ("kind", "url", "code"),
        [
            ("recorded_replay", "file:///etc/passwd", "unsupported_scheme"),
            ("recorded_replay", "replay://../../etc/passwd", "invalid_replay_reference"),
            ("recorded_replay", "replay:///abs/path.mp4", "invalid_replay_reference"),
            ("authorized_network_live", "http://cam.example.org/x", "unsupported_scheme"),
            ("authorized_network_live", "replay://x.mp4", "unsupported_scheme"),
            ("authorized_network_live", "rtsp://user:pw@/x", "invalid_source_url"),
            ("authorized_network_live", "rtsp://cam.example.org:99999/x", "invalid_source_url"),
            ("authorized_network_live", "rtsp://cam example.org/x", "invalid_source_url"),
            ("owned_optical_live", "gopher://x", "unsupported_scheme"),
        ],
    )
    def test_rejected_without_echoing_the_url(self, kind: str, url: str, code: str) -> None:
        with pytest.raises(ControlError) as exc:
            ctl.parse_source(kind, url)
        assert exc.value.code == code
        assert url not in json.dumps(exc.value.detail())
        assert "pw" not in exc.value.message

    def test_worker_messages_are_sanitized(self) -> None:
        msg = ctl.sanitize_message(f"cannot open {SECRET_URL}: password=hunter2 timeout")
        assert msg is not None
        assert not any(m in msg for m in SECRET_MARKERS) and "hunter2" not in msg


# --------------------------------------------------------------------------- unit: eligibility


def _cam(**kw: Any) -> Camera:
    base = {
        "id": uuid.uuid4(),
        "lifecycle_state": "onboarding",
        "source_kind": "recorded_replay",
        "source_display": "replay://x.mp4",
    }
    return Camera(**{**base, **kw})


def _grant(camera: Camera, **kw: Any) -> CameraSourceGrant:
    now = datetime.now(UTC)
    base = {
        "camera_id": camera.id,
        "status": "active",
        "valid_from": now - timedelta(days=1),
        "valid_until": now + timedelta(days=1),
        "capture_method": "recorded_replay",
        "max_analysis_fps": 30.0,
        "max_frame_height": 1080,
        "media_scope": "events_only",
        "export_allowed": False,
    }
    return CameraSourceGrant(**{**base, **kw})


def _version(camera: Camera, status: str = "approved", cfg: dict[str, Any] | None = None) -> Any:
    return CameraConfigVersion(camera_id=camera.id, status=status, config=cfg or config())


def codes(unmet: list[ctl.Unmet]) -> set[str]:
    return {u.code for u in unmet}


class TestEligibility:
    """A04 (pure function): absent/expired/insufficient grants are all reported at once."""

    def test_eligible(self) -> None:
        cam = _cam()
        assert ctl.evaluate_eligibility(cam, [_grant(cam)], _version(cam)) == []

    def test_everything_missing_is_reported_together(self) -> None:
        cam = _cam(source_kind=None, source_display=None)
        assert codes(ctl.evaluate_eligibility(cam, [], None)) == {
            "source_missing",
            "config_missing",
            "grant_missing",
        }

    @pytest.mark.parametrize(
        ("grant_kw", "expected"),
        [
            (
                {
                    "valid_until": datetime.now(UTC) - timedelta(seconds=1),
                    "valid_from": datetime.now(UTC) - timedelta(days=2),
                },
                {"grant_expired"},
            ),
            (
                {
                    "valid_from": datetime.now(UTC) + timedelta(days=1),
                    "valid_until": datetime.now(UTC) + timedelta(days=2),
                },
                {"grant_not_yet_valid"},
            ),
            ({"status": "revoked"}, {"grant_revoked"}),
            ({"capture_method": "authorized_network_live"}, {"grant_capture_method_mismatch"}),
            ({"max_analysis_fps": 10.0}, {"grant_fps_exceeded"}),
            (
                {"max_frame_height": 720, "status": "revoked"},
                {"grant_resolution_exceeded", "grant_revoked"},
            ),
        ],
    )
    def test_grant_matrix(self, grant_kw: dict[str, Any], expected: set[str]) -> None:
        cam = _cam()
        assert codes(ctl.evaluate_eligibility(cam, [_grant(cam, **grant_kw)], _version(cam))) == (
            expected
        )

    def test_best_grant_wins(self) -> None:
        cam = _cam()
        grants = [_grant(cam, status="revoked"), _grant(cam)]
        assert ctl.evaluate_eligibility(cam, grants, _version(cam)) == []

    @pytest.mark.parametrize(
        ("cam_kw", "status", "expected"),
        [
            ({"lifecycle_state": "legacy"}, "approved", {"camera_not_managed"}),
            ({"lifecycle_state": "discovered"}, "approved", {"camera_not_onboarded"}),
            ({}, "draft", {"config_not_approved"}),
            ({}, "awaiting_approval", {"config_not_approved"}),
        ],
    )
    def test_camera_and_version_state(
        self, cam_kw: dict[str, Any], status: str, expected: set[str]
    ) -> None:
        cam = _cam(**cam_kw)
        assert codes(ctl.evaluate_eligibility(cam, [_grant(cam)], _version(cam, status))) == (
            expected
        )

    def test_invalid_config_is_reported(self) -> None:
        cam = _cam()
        bad = _version(cam, cfg=config(rules=["nope"]))
        assert codes(ctl.evaluate_eligibility(cam, [_grant(cam)], bad)) == {"config_invalid"}


# --------------------------------------------------------------------------- API helpers


class Ctl:
    """Drives the control-plane API like the admin UI does."""

    def __init__(self, client: ApiClient) -> None:
        self.c = client

    def create_camera(self, slug: str = "e2e-replay", **kw: Any) -> dict[str, Any]:
        r = self.c.post(
            "/api/cameras", {"name": f"Camera {slug}", "location": "Test site", "slug": slug, **kw}
        )
        assert r.status_code == 201, r.text
        return dict(r.json())

    def detail(self, cam: str) -> dict[str, Any]:
        r = self.c.get(f"{BASE}/{cam}")
        assert r.status_code == 200, r.text
        return dict(r.json())

    def rev(self, cam: str) -> int:
        return int(self.detail(cam)["revision"])

    def source(
        self,
        cam: str,
        url: str = "replay://data/videos/vehicles-2.mp4",
        kind: str = "recorded_replay",
    ) -> Any:
        return self.c.post(
            f"{BASE}/{cam}/source",
            {"kind": kind, "url": url, "expected_revision": self.rev(cam), "reason": "register"},
        )

    def grant(self, cam: str, **kw: Any) -> Any:
        return self.c.post(f"{BASE}/{cam}/grants", grant_body(**kw))

    def draft(self, cam: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
        r = self.c.post(f"{BASE}/{cam}/versions", {"config": cfg or config(), "reason": "test"})
        assert r.status_code == 201, r.text
        return dict(r.json())

    def act(self, cam: str, version: str, action: str, body: dict[str, Any] | None = None) -> Any:
        return self.c.post(f"{BASE}/{cam}/versions/{version}/{action}", body or {})

    def activate(
        self, cam: str, version: str, rev: int | None = None, path: str = "activate"
    ) -> Any:
        return self.c.post(
            f"{BASE}/{cam}/{path}",
            {
                "version_id": version,
                "expected_revision": self.rev(cam) if rev is None else rev,
                "reason": "go live",
            },
        )

    def camera_action(self, cam: str, action: str, rev: int | None = None) -> Any:
        return self.c.post(
            f"{BASE}/{cam}/{action}",
            {"expected_revision": self.rev(cam) if rev is None else rev, "reason": "test action"},
        )


@pytest.fixture
def admin2(world: World) -> Any:
    return make_user(world.a.id, Role.tenant_admin, "admin2.a@test.local")


@pytest.fixture
def a1(world: World, login: Any) -> Ctl:
    return Ctl(login(world.a.admin))


@pytest.fixture
def a2(admin2: Any, login: Any) -> Ctl:
    return Ctl(login(admin2))


def approved_version(
    author: Ctl, approver: Ctl, cam: str, cfg: dict[str, Any] | None = None
) -> str:
    v = author.draft(cam, cfg)
    assert author.act(cam, v["id"], "validate").json()["status"] == "validated"
    assert author.act(cam, v["id"], "submit").json()["status"] == "awaiting_approval"
    r = approver.act(cam, v["id"], "approve", {"note": "reviewed"})
    assert r.status_code == 200 and r.json()["status"] == "approved", r.text
    return str(v["id"])


def ready_camera(a1: Ctl, a2: Ctl, slug: str = "e2e-replay") -> tuple[str, str]:
    cam = a1.create_camera(slug)["id"]
    assert a1.source(cam).status_code == 200
    assert a1.grant(cam).status_code == 201
    return cam, approved_version(a1, a2, cam)


def worker_get(pipe: Pipeline, target: str) -> Any:
    return pipe.http.get(target, headers=pipe.headers("GET", target, b""))


def heartbeat(pipe: Pipeline, slug: str, **body: Any) -> Any:
    payload = {"worker_epoch": "epoch-aaaa", "seq": 1, "health": "healthy", **body}
    return pipe.post(f"/api/ingest/cameras/{slug}/heartbeat", json.dumps(payload).encode())


def ack(pipe: Pipeline, slug: str, **body: Any) -> Any:
    return pipe.post(f"/api/ingest/cameras/{slug}/config/ack", json.dumps(body).encode())


def audit_rows(tenant_id: uuid.UUID) -> list[tuple[str, str]]:
    with admin_conn() as conn:
        rows = conn.execute(
            "SELECT action, details::text FROM audit_log WHERE tenant_id = %s ORDER BY seq",
            (tenant_id,),
        ).fetchall()
    return [(r[0], r[1]) for r in rows]


# --------------------------------------------------------------------------- API: RBAC


MUTATIONS = [
    ("patch", "", {"expected_revision": 0, "reason": "xxx", "name": "New name"}),
    ("post", "/lifecycle", {"to": "onboarding", "expected_revision": 0, "reason": "xxx"}),
    (
        "post",
        "/source",
        {
            "kind": "recorded_replay",
            "url": "replay://x.mp4",
            "expected_revision": 0,
            "reason": "xxx",
        },
    ),
    ("post", "/grants", grant_body()),
    ("post", "/config/validate", {"config": VALID}),
    ("post", "/versions", {"config": VALID, "reason": "xxx"}),
    (
        "post",
        "/activate",
        {"version_id": str(uuid.uuid4()), "expected_revision": 0, "reason": "xxx"},
    ),
    (
        "post",
        "/rollback",
        {"version_id": str(uuid.uuid4()), "expected_revision": 0, "reason": "xxx"},
    ),
    ("post", "/pause", {"expected_revision": 0, "reason": "xxx"}),
    ("post", "/resume", {"expected_revision": 0, "reason": "xxx"}),
    ("post", "/disable", {"expected_revision": 0, "reason": "xxx"}),
    ("post", "/enable-request", {"expected_revision": 0, "reason": "xxx"}),
    ("post", "/enable", {"expected_revision": 0, "reason": "xxx"}),
    ("post", f"/versions/{uuid.uuid4()}/validate", {}),
    ("post", f"/versions/{uuid.uuid4()}/submit", {}),
    ("post", f"/versions/{uuid.uuid4()}/approve", {}),
    ("post", f"/versions/{uuid.uuid4()}/reject", {}),
    ("post", f"/grants/{uuid.uuid4()}/revoke", {"reason": "xxx"}),
]
READS = ["", "/versions", "/grants", "/eligibility", "/health"]


class TestRbac:
    """A01: only tenant admins mutate; operators/auditors read; patrol sees nothing."""

    @pytest.mark.parametrize("role", [Role.operator, Role.auditor, Role.patrol])
    @pytest.mark.parametrize(("method", "suffix", "body"), MUTATIONS)
    def test_non_admins_cannot_mutate(
        self, world: World, login: Any, role: Role, method: str, suffix: str, body: Any
    ) -> None:
        c = login(world.a.users[role])
        r = getattr(c, method)(f"{BASE}/{world.data['a']['camera']}{suffix}", json=body)
        assert r.status_code == 403, (role, suffix, r.text)

    @pytest.mark.parametrize("role", [Role.operator, Role.auditor, Role.patrol])
    def test_non_admins_cannot_create_cameras(self, world: World, login: Any, role: Role) -> None:
        r = login(world.a.users[role]).post("/api/cameras", {"name": "xx", "location": "yy"})
        assert r.status_code == 403

    @pytest.mark.parametrize(
        ("role", "expected"),
        [(Role.tenant_admin, 200), (Role.operator, 200), (Role.auditor, 200), (Role.patrol, 403)],
    )
    def test_reads(self, world: World, login: Any, role: Role, expected: int) -> None:
        c = login(world.a.users[role])
        assert c.get(BASE).status_code == expected
        for suffix in READS:
            r = c.get(f"{BASE}/{world.data['a']['camera']}{suffix}")
            assert r.status_code == expected, (role, suffix, r.text)

    def test_mutations_need_csrf(self, world: World, login: Any) -> None:
        c = login(world.a.admin)
        r = c.http.post(
            f"{BASE}/{world.data['a']['camera']}/pause",
            json={"expected_revision": 0, "reason": "xxx"},
            headers={"Origin": "https://testserver"},
        )
        assert r.status_code == 403


class TestTenantIsolation:
    """A03: tenant B never lists, reads, edits or activates tenant A's camera."""

    def test_cross_tenant_probe_is_a_plain_404(self, world: World, login: Any) -> None:
        b = login(world.b.admin)
        cam_a = world.data["a"]["camera"]
        missing = uuid.uuid4()
        for method, suffix, body in [("get", "", None), *MUTATIONS[:3], MUTATIONS[6]]:
            kw = {"json": body} if body is not None else {}
            r_a = getattr(b, method)(f"{BASE}/{cam_a}{suffix}", **kw)
            r_x = getattr(b, method)(f"{BASE}/{missing}{suffix}", **kw)
            assert r_a.status_code == r_x.status_code == 404, (suffix, r_a.text)
            assert r_a.json() == r_x.json()
        assert str(cam_a) not in json.dumps(b.get(BASE).json())
        assert "security.cross_tenant_access" in audit_actions(world.a.id)

    def test_worker_of_tenant_b_cannot_read_tenant_a_config(self, world: World) -> None:
        pipe_b, _ = make_pipeline(world.b.id)
        with admin_conn() as conn:
            slug = conn.execute(
                "SELECT slug FROM cameras WHERE id = %s", (world.data["a"]["camera"],)
            ).fetchone()[0]
        assert worker_get(pipe_b, f"/api/ingest/cameras/{slug}/config").status_code == 422


# --------------------------------------------------------------------------- API: lifecycle


class TestLifecycle:
    def test_created_camera_is_not_enabled(self, world: World, a1: Ctl) -> None:
        """A02/A20: an API-created camera is onboarding, never enabled, and its evidence is
        refused until an approved config is activated under a valid grant."""
        cam = a1.create_camera("new-cam")
        assert cam["lifecycle_state"] == "onboarding" and cam["desired_enabled"] is False
        d = a1.detail(cam["id"])
        assert d["runtime"]["state"] == "onboarding" and d["runtime"]["runnable"] is False
        pipe, _ = make_pipeline(world.a.id)
        r = worker_get(pipe, "/api/ingest/cameras/new-cam/config")
        assert r.status_code == 200 and r.json()["run"] is False and r.json()["config"] is None
        ev = {
            "camera_id": "new-cam",
            "type": "congestion",
            "occurred_at": "2026-11-09T10:00:00",
            "video_t": 1.0,
            "rule": "synthetic test event",
            "vlm_status": "skipped",
        }
        r = send(
            pipe,
            "POST",
            "/api/ingest/events",
            data={"event": json.dumps(ev)},
            files={"keyframe": ("k.jpg", JPEG, "image/jpeg"), "clip": ("c.mp4", MP4, "video/mp4")},
        )
        assert r.status_code == 403 and r.json()["detail"]["code"] == "camera_not_authorized"
        assert "ingest.camera_blocked" in audit_actions(world.a.id)

    def test_discovered_candidate_cannot_be_configured(self, a1: Ctl) -> None:
        cam = a1.create_camera("candidate", lifecycle_state="discovered")["id"]
        r = a1.c.post(f"{BASE}/{cam}/versions", {"config": VALID, "reason": "try"})
        assert r.status_code == 409 and r.json()["detail"]["code"] == "camera_not_onboarded"
        r = a1.c.post(
            f"{BASE}/{cam}/lifecycle",
            {"to": "onboarding", "expected_revision": 0, "reason": "reviewed"},
        )
        assert r.status_code == 200 and r.json()["lifecycle_state"] == "onboarding"

    def test_duplicate_slug_is_refused(self, a1: Ctl) -> None:
        a1.create_camera("dup")
        r = a1.c.post("/api/cameras", {"name": "Other", "location": "x y", "slug": "dup"})
        assert r.status_code == 409 and r.json()["detail"]["code"] == "duplicate_camera_id"

    def test_rename_keeps_identity(self, a1: Ctl) -> None:
        cam = a1.create_camera("stable-id")["id"]
        r = a1.c.patch(
            f"{BASE}/{cam}", {"expected_revision": 0, "reason": "rename", "name": "Nume nou"}
        )
        assert r.status_code == 200 and r.json()["slug"] == "stable-id"
        assert r.json()["name"] == "Nume nou" and r.json()["revision"] == 1
        stale = a1.c.patch(
            f"{BASE}/{cam}", {"expected_revision": 0, "reason": "rename", "name": "Alt nume"}
        )
        assert stale.status_code == 409
        assert stale.json()["detail"] == {
            "code": "revision_conflict",
            "message": "The camera changed since it was loaded; reload and retry",
            "current_revision": 1,
        }

    def test_adopting_a_legacy_camera_gates_its_ingest(self, world: World, a1: Ctl) -> None:
        cam = world.data["a"]["camera"]
        assert a1.detail(cam)["lifecycle_state"] == "legacy"
        r = a1.c.post(
            f"{BASE}/{cam}/lifecycle",
            {"to": "onboarding", "expected_revision": 0, "reason": "adopt"},
        )
        assert r.status_code == 200
        pipe, _ = make_pipeline(world.a.id)
        slug = a1.detail(cam)["slug"]
        r = send(
            pipe,
            "PUT",
            f"/api/ingest/cameras/{slug}/video",
            files={"video": ("v.mp4", MP4, "video/mp4")},
        )
        assert r.status_code == 403


class TestVersionsAndApproval:
    def test_validate_without_capture(self, world: World, a1: Ctl) -> None:
        """A05: validating a draft changes nothing at runtime."""
        cam = a1.create_camera()["id"]
        v = a1.draft(cam)
        assert v["status"] == "draft" and v["validation_errors"] == []
        r = a1.act(cam, v["id"], "validate")
        assert r.json()["status"] == "validated"
        d = a1.detail(cam)
        assert d["desired_enabled"] is False and d["worker"] is None
        assert d["active_version_id"] is None

    def test_invalid_draft_keeps_errors_and_cannot_advance(self, a1: Ctl) -> None:
        """A06 via the API, with the documented error shape."""
        cam = a1.create_camera()["id"]
        dry = a1.c.post(f"{BASE}/{cam}/config/validate", {"config": INVALID["config"]})
        assert dry.status_code == 200 and dry.json()["valid"] is False
        assert {(e["path"], e["code"]) for e in dry.json()["errors"]} == {
            (e["path"], e["code"]) for e in INVALID["expected_errors"]
        }
        assert all(set(e) == {"path", "code", "message"} for e in dry.json()["errors"])
        assert "hunter2" not in dry.text
        v = a1.draft(cam, INVALID["config"])
        assert a1.act(cam, v["id"], "validate").json()["status"] == "draft"
        r = a1.act(cam, v["id"], "submit")
        assert r.status_code == 409 and r.json()["detail"]["code"] == "invalid_transition"

    def test_four_eyes(self, world: World, a1: Ctl, a2: Ctl) -> None:
        """A07: the author/submitter cannot approve; a second admin can."""
        cam = a1.create_camera()["id"]
        v = a1.draft(cam)
        a1.act(cam, v["id"], "validate")
        a1.act(cam, v["id"], "submit")
        r = a1.act(cam, v["id"], "approve")
        assert r.status_code == 403 and r.json()["detail"]["code"] == "four_eyes_required"
        assert any(
            a == "camera.control.refused" and "four_eyes_required" in d
            for a, d in audit_rows(world.a.id)
        )
        assert a2.act(cam, v["id"], "approve").json()["status"] == "approved"
        # The database refuses a same-person decision even if the service were bypassed.
        v2 = a1.draft(cam, config(min_y=630))
        with app_conn() as conn, pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(world.a.id),))
            conn.execute(
                "UPDATE camera_config_versions SET decided_by = created_by WHERE id = %s",
                (v2["id"],),
            )

    def test_versions_are_immutable_in_the_database(self, world: World, a1: Ctl, a2: Ctl) -> None:
        """A08: config, fingerprint and revision cannot change; rows cannot be deleted."""
        cam = a1.create_camera()["id"]
        vid = approved_version(a1, a2, cam)
        for sql in (
            "UPDATE camera_config_versions SET config = '{}'::jsonb WHERE id = %s",
            "UPDATE camera_config_versions SET fingerprint = repeat('0', 64) WHERE id = %s",
            "UPDATE camera_config_versions SET status = 'draft' WHERE id = %s",
            "DELETE FROM camera_config_versions WHERE id = %s",
        ):
            with app_conn() as conn, pytest.raises(psycopg.Error):
                conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(world.a.id),))
                conn.execute(sql, (vid,))

    def test_reject(self, a1: Ctl, a2: Ctl) -> None:
        cam = a1.create_camera()["id"]
        v = a1.draft(cam)
        assert a1.act(cam, v["id"], "reject").status_code == 403
        r = a2.act(cam, v["id"], "reject", {"note": "wrong zones"})
        assert r.json()["status"] == "rejected"
        assert a2.act(cam, v["id"], "validate").json()["status"] == "rejected"

    def test_diff_endpoint(self, a1: Ctl, a2: Ctl) -> None:
        cam, v1 = ready_camera(a1, a2)
        v2 = a1.draft(cam, config(min_y=640))
        assert a1.activate(cam, v1).status_code == 200
        d = a1.c.get(f"{BASE}/{cam}/versions/{v2['id']}/diff").json()
        assert d["from_version_id"] == v1 and d["changes"] == [
            {"path": "min_y", "op": "changed", "before": 620, "after": 640}
        ]


class TestActivation:
    def test_requires_grant(self, world: World, a1: Ctl, a2: Ctl) -> None:
        """A04: absent, then expired authorization blocks activation (all unmet listed)."""
        cam = a1.create_camera()["id"]
        vid = approved_version(a1, a2, cam)
        r = a1.activate(cam, vid)
        assert r.status_code == 409 and r.json()["detail"]["code"] == "not_eligible"
        assert {u["code"] for u in r.json()["detail"]["unmet"]} == {
            "source_missing",
            "grant_missing",
        }
        a1.source(cam)
        now = datetime.now(UTC)
        a1.grant(
            cam,
            valid_from=(now - timedelta(days=9)).isoformat(),
            valid_until=(now - timedelta(days=1)).isoformat(),
        )
        r = a1.activate(cam, vid)
        assert [u["code"] for u in r.json()["detail"]["unmet"]] == ["grant_expired"]
        dry = a1.c.get(f"{BASE}/{cam}/eligibility", params={"version_id": vid}).json()
        assert dry["eligible"] is False and dry["unmet"][0]["code"] == "grant_expired"
        assert a1.detail(cam)["active_version_id"] is None

    def test_activation_persists_actor_reason_and_fingerprints(
        self, world: World, a1: Ctl, a2: Ctl
    ) -> None:
        """A08."""
        cam, vid = ready_camera(a1, a2)
        r = a1.activate(cam, vid)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["changed"] is True and body["version"]["status"] == "active"
        assert body["version"]["activated_by"] == str(world.a.admin.id)
        assert body["version"]["activation_reason"] == "go live"
        assert body["camera"]["lifecycle_state"] == "approved"
        assert body["camera"]["desired_enabled"] is True
        _action, details = [x for x in audit_rows(world.a.id) if x[0] == "camera.config.activated"][
            -1
        ]
        d = json.loads(details)
        assert d["after_fingerprint"] == body["version"]["fingerprint"]
        assert d["before_fingerprint"] is None and d["reason"] == "go live"

    def test_idempotent_and_stale_revision(self, a1: Ctl, a2: Ctl) -> None:
        cam, vid = ready_camera(a1, a2)
        rev = a1.rev(cam)
        first = a1.activate(cam, vid, rev)
        again = a1.activate(cam, vid, rev)  # retried request with the same (now stale) revision
        assert first.status_code == again.status_code == 200
        assert again.json()["changed"] is False
        assert again.json()["camera"]["revision"] == first.json()["camera"]["revision"]
        v2 = approved_version(a1, a2, cam, config(min_y=640))
        stale = a1.activate(cam, v2, rev)
        assert stale.status_code == 409 and stale.json()["detail"]["code"] == "revision_conflict"

    def test_concurrent_activations_have_one_winner(self, world: World, a1: Ctl, a2: Ctl) -> None:
        """A09: two admins activate different approved versions with the same expected revision
        at the same moment: exactly one succeeds, the other gets 409, nothing is lost."""
        cam, v1 = ready_camera(a1, a2)
        v2 = approved_version(a2, a1, cam, config(min_y=640))
        rev = a1.rev(cam)
        barrier = threading.Barrier(2)
        results: dict[str, Any] = {}

        def run(name: str, who: Ctl, vid: str) -> None:
            barrier.wait()
            results[name] = who.activate(cam, vid, rev)

        threads = [
            threading.Thread(target=run, args=("a1", a1, v1)),
            threading.Thread(target=run, args=("a2", a2, v2)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        statuses = sorted(r.status_code for r in results.values())
        assert statuses == [200, 409], {k: r.text for k, r in results.items()}
        winner = next(r for r in results.values() if r.status_code == 200).json()
        loser = next(r for r in results.values() if r.status_code == 409).json()
        assert loser["detail"]["code"] == "revision_conflict"
        d = a1.detail(cam)
        assert d["active_version_id"] == winner["version"]["id"]
        assert d["revision"] == rev + 1
        with admin_conn() as conn:
            active = conn.execute(
                "SELECT count(*) FROM camera_config_versions WHERE camera_id = %s "
                "AND status = 'active'",
                (cam,),
            ).fetchone()[0]
        assert active == 1

    def test_rollback_reactivates_a_prior_version_without_changing_it(
        self, a1: Ctl, a2: Ctl
    ) -> None:
        cam, v1 = ready_camera(a1, a2)
        v2 = approved_version(a1, a2, cam, config(min_y=640))
        fp1 = a1.c.get(f"{BASE}/{cam}/versions/{v1}").json()["fingerprint"]
        assert a1.activate(cam, v1).status_code == 200
        assert a1.activate(cam, v2).status_code == 200
        bad = a1.activate(cam, v2, path="rollback")
        assert bad.status_code == 200 and bad.json()["changed"] is False  # already active
        r = a1.activate(cam, v1, path="rollback")
        assert r.status_code == 200 and r.json()["version"]["status"] == "active"
        versions = {v["id"]: v for v in a1.c.get(f"{BASE}/{cam}/versions").json()}
        assert versions[v2]["status"] == "superseded" and versions[v1]["fingerprint"] == fp1
        v3 = a1.draft(cam, config(min_y=650))["id"]
        assert a1.activate(cam, v3, path="rollback").status_code == 409

    def test_pause_disable_and_four_eyes_enable(self, world: World, a1: Ctl, a2: Ctl) -> None:
        """A14: pause/resume/disable/enable are real; restart is honestly unsupported."""
        cam, vid = ready_camera(a1, a2)
        a1.activate(cam, vid)
        pipe, _ = make_pipeline(world.a.id)
        slug = "e2e-replay"
        assert worker_get(pipe, f"/api/ingest/cameras/{slug}/config").json()["run"] is True
        assert a1.camera_action(cam, "pause").json()["runtime"]["state"] == "paused"
        cfg = worker_get(pipe, f"/api/ingest/cameras/{slug}/config").json()
        assert cfg["run"] is False and cfg["reason"] == "paused" and cfg["config"] is None
        assert a1.camera_action(cam, "resume").json()["desired_enabled"] is True
        assert a1.camera_action(cam, "disable").json()["lifecycle_state"] == "disabled"
        assert heartbeat(pipe, slug).json()["directive"] == "stop"
        r = a1.camera_action(cam, "enable")
        assert r.status_code == 409 and r.json()["detail"]["code"] == "enable_not_requested"
        assert a1.camera_action(cam, "enable-request").status_code == 200
        r = a1.camera_action(cam, "enable")
        assert r.status_code == 403 and r.json()["detail"]["code"] == "four_eyes_required"
        r = a2.camera_action(cam, "enable")
        assert r.status_code == 200 and r.json()["lifecycle_state"] == "approved"
        assert "restart" in a1.detail(cam)["unsupported_actions"]

    def test_source_change_requires_reapproval(self, a1: Ctl, a2: Ctl) -> None:
        cam, vid = ready_camera(a1, a2)
        a1.activate(cam, vid)
        r = a1.source(cam, "replay://data/videos/other.mp4")
        assert r.json()["lifecycle_state"] == "disabled"
        assert r.json()["disabled_reason"] == "source_changed"

    def test_pending_enable_request_does_not_survive_a_source_change(
        self, a1: Ctl, a2: Ctl
    ) -> None:
        cam, vid = ready_camera(a1, a2)
        a1.activate(cam, vid)
        assert a1.camera_action(cam, "disable").status_code == 200
        assert a2.camera_action(cam, "enable-request").status_code == 200
        assert a1.source(cam, "replay://data/videos/other.mp4").status_code == 200
        r = a1.camera_action(cam, "enable")
        assert r.status_code == 409 and r.json()["detail"]["code"] == "enable_not_requested"

    def test_legacy_camera_with_a_running_worker(self, world: World, a1: Ctl) -> None:
        """Its heartbeat counts (never "never seen"), and it cannot be adopted while running:
        the worker's events would start being refused."""
        cam = a1.create_camera("legacy-live")["id"]
        with admin_conn() as conn:
            conn.execute(
                "UPDATE cameras SET lifecycle_state='legacy', last_seen_at=now() WHERE id=%s",
                (cam,),
            )
        runtime = a1.detail(cam)["runtime"]
        assert runtime["state"] == "processing" and runtime["freshness"] == "fresh"
        assert runtime["is_live"] is False
        body = {"to": "onboarding", "expected_revision": a1.rev(cam), "reason": "adopt"}
        r = a1.c.post(f"{BASE}/{cam}/lifecycle", body)
        assert r.status_code == 409 and r.json()["detail"]["code"] == "worker_active"
        with admin_conn() as conn:
            conn.execute(
                "UPDATE cameras SET last_seen_at=now() - interval '1 hour' WHERE id=%s", (cam,)
            )
        assert a1.c.post(f"{BASE}/{cam}/lifecycle", body).status_code == 200

    def test_legacy_camera_cannot_be_disabled(self, a1: Ctl) -> None:
        """Nothing could bring it back: its ingest must keep working until it is adopted."""
        cam = a1.create_camera("legacy-keep")["id"]
        with admin_conn() as conn:
            conn.execute("UPDATE cameras SET lifecycle_state='legacy' WHERE id=%s", (cam,))
        r = a1.camera_action(cam, "disable")
        assert r.status_code == 409 and r.json()["detail"]["code"] == "camera_not_managed"
        assert a1.detail(cam)["lifecycle_state"] == "legacy"

    @pytest.mark.parametrize("bad", ["NaN", '"x\\u0000y"'])
    def test_unstorable_json_is_a_422(self, a1: Ctl, bad: str) -> None:
        cam = a1.create_camera("bad-json")["id"]
        body = '{"reason": "try", "config": {"a": ' + bad + "}}"
        headers = a1.c._headers({"content-type": "application/json"})
        r = a1.c.http.post(f"{BASE}/{cam}/versions", content=body, headers=headers)
        assert r.status_code == 422 and r.json()["detail"]["code"] == "invalid_config", r.text

    def test_revoked_grant_blocks_runtime(self, world: World, a1: Ctl, a2: Ctl) -> None:
        cam, vid = ready_camera(a1, a2)
        a1.activate(cam, vid)
        gid = a1.c.get(f"{BASE}/{cam}/grants").json()[0]["id"]
        assert (
            a1.c.post(f"{BASE}/{cam}/grants/{gid}/revoke", {"reason": "owner withdrew"}).json()[
                "status"
            ]
            == "revoked"
        )
        d = a1.detail(cam)
        assert d["runtime"]["state"] == "permission_blocked"
        assert {u["code"] for u in d["runtime"]["unmet"]} == {"grant_revoked"}
        pipe, _ = make_pipeline(world.a.id)
        cfg = worker_get(pipe, "/api/ingest/cameras/e2e-replay/config").json()
        assert cfg["run"] is False and cfg["reason"] == "not_authorized"


# --------------------------------------------------------------------------- worker handshake


@pytest.fixture
def live_camera(world: World, a1: Ctl, a2: Ctl) -> tuple[str, str, Pipeline, Pipeline]:
    cam, vid = ready_camera(a1, a2)
    assert a1.activate(cam, vid).status_code == 200
    scoped, _ = make_pipeline(world.a.id, "scoped", camera_ids=[uuid.UUID(cam)])
    other, _ = make_pipeline(world.a.id, "other", camera_ids=[world.data["a"]["camera"]])
    return cam, vid, scoped, other


class TestWorker:
    def test_scoped_worker_gets_only_its_active_config(
        self, live_camera: Any, a1: Ctl, a2: Ctl
    ) -> None:
        """A10: the key for camera X cannot read camera Y; only ACTIVE config is delivered."""
        cam, _vid, scoped, other = live_camera
        assert worker_get(other, "/api/ingest/cameras/e2e-replay/config").status_code == 403
        r = worker_get(scoped, "/api/ingest/cameras/e2e-replay/config")
        body = r.json()
        assert r.status_code == 200 and body["run"] is True and body["revision"] == 1
        assert body["fingerprint"] == cc.fingerprint(body["config"])
        assert body["source_kind"] == "recorded_replay"
        a1.draft(cam, config(min_y=700))  # a newer DRAFT is never delivered
        assert worker_get(scoped, "/api/ingest/cameras/e2e-replay/config").json()["revision"] == 1
        assert "video" not in json.dumps(body["config"])

    def test_ack_and_reject_keep_last_known_good(self, live_camera: Any, a1: Ctl, a2: Ctl) -> None:
        """A11/A12: an accepted revision becomes applied; rejecting a newer one keeps it."""
        cam, _vid, scoped, _ = live_camera
        cfg = worker_get(scoped, "/api/ingest/cameras/e2e-replay/config").json()
        epoch = "worker-epoch-1"
        assert heartbeat(scoped, "e2e-replay", worker_epoch=epoch).json()["lease"] == "holder"
        r = ack(
            scoped,
            "e2e-replay",
            worker_epoch=epoch,
            revision=1,
            fingerprint=cfg["fingerprint"],
            status="accepted",
        )
        assert r.status_code == 200 and r.json()["applied_revision"] == 1
        v2 = approved_version(a1, a2, cam, config(min_y=640))
        assert a1.activate(cam, v2).status_code == 200
        new = worker_get(scoped, "/api/ingest/cameras/e2e-replay/config").json()
        r = ack(
            scoped,
            "e2e-replay",
            worker_epoch=epoch,
            revision=new["revision"],
            fingerprint=new["fingerprint"],
            status="rejected",
            reason_code="reference_frame_mismatch",
            message="frame is 1280x720",
        )
        assert r.status_code == 200 and r.json()["applied_revision"] == 1
        rt = a1.detail(cam)["runtime"]
        assert (rt["desired_revision"], rt["applied_revision"], rt["revision_in_sync"]) == (
            2,
            1,
            False,
        )
        assert a1.detail(cam)["worker"]["last_ack_reason"] == "reference_frame_mismatch"
        bogus = ack(
            scoped,
            "e2e-replay",
            worker_epoch=epoch,
            revision=2,
            fingerprint="0" * 64,
            status="accepted",
        )
        assert bogus.status_code == 422

    def test_stale_and_replay_are_never_live(self, live_camera: Any, a1: Ctl) -> None:
        """A13: a fresh healthy replay is 'replay' (not live); an old heartbeat is 'stale'."""
        cam, _, scoped, _ = live_camera
        assert a1.detail(cam)["runtime"]["state"] == "never_seen"
        heartbeat(scoped, "e2e-replay", source_fps=25, processing_fps=12.5, model_id="yolo11s.pt")
        rt = a1.detail(cam)["runtime"]
        assert (rt["state"], rt["is_live"], rt["freshness"]) == ("replay", False, "fresh")
        with admin_conn() as conn:
            conn.execute(
                "UPDATE camera_worker_status SET last_heartbeat_at = now() - interval '5 minutes'"
                " WHERE camera_id = %s",
                (cam,),
            )
        rt = a1.detail(cam)["runtime"]
        assert (rt["state"], rt["is_live"], rt["freshness"]) == ("stale", False, "stale")
        assert rt["heartbeat_age_s"] >= 290
        heartbeat(
            scoped,
            "e2e-replay",
            seq=2,
            health="decoder_failed",
            error_code="decode",
            error_message=f"cannot decode {SECRET_URL}",
        )
        d = a1.detail(cam)
        assert d["runtime"]["state"] == "decoder_failed"
        assert not any(m in json.dumps(d) for m in SECRET_MARKERS)

    def test_live_source_is_live_only_while_fresh(self, world: World, a1: Ctl, a2: Ctl) -> None:
        cam = a1.create_camera("net-cam")["id"]
        a1.source(cam, "https://hls.example.org/cam/index.m3u8", "authorized_network_live")
        a1.grant(cam, capture_method="authorized_network_live")
        vid = approved_version(a1, a2, cam)
        assert a1.activate(cam, vid).status_code == 200
        pipe, _ = make_pipeline(world.a.id)
        heartbeat(pipe, "net-cam")
        assert a1.detail(cam)["runtime"]["is_live"] is True

    def test_duplicate_workers(self, live_camera: Any, a1: Ctl) -> None:
        """A15: a second worker epoch is told to stop while the first holds the lease."""
        cam, _, scoped, _ = live_camera
        first = heartbeat(scoped, "e2e-replay", worker_epoch="epoch-first").json()
        assert (first["lease"], first["directive"]) == ("holder", "run")
        second = heartbeat(scoped, "e2e-replay", worker_epoch="epoch-second").json()
        assert (second["lease"], second["directive"], second["reason"]) == (
            "standby",
            "stop",
            "duplicate_worker",
        )
        d = a1.detail(cam)
        assert d["runtime"]["duplicate_worker"] is True
        assert d["worker"]["lease_epoch"] == "epoch-first"
        # The standby epoch cannot ack either.
        cfg = worker_get(scoped, "/api/ingest/cameras/e2e-replay/config").json()
        r = ack(
            scoped,
            "e2e-replay",
            worker_epoch="epoch-second",
            revision=1,
            fingerprint=cfg["fingerprint"],
            status="accepted",
        )
        assert r.status_code == 409
        # A graceful stop releases the lease; the other epoch may then take over.
        heartbeat(scoped, "e2e-replay", worker_epoch="epoch-first", seq=2, health="stopped")
        took = heartbeat(scoped, "e2e-replay", worker_epoch="epoch-second", seq=5).json()
        assert (took["lease"], took["directive"]) == ("holder", "run")
        kinds = [e["kind"] for e in a1.c.get(f"{BASE}/{cam}/health").json()]
        assert "lease_conflict" in kinds and kinds.count("lease_acquired") == 2

    def test_applied_revision_follows_the_lease_holder(self, live_camera: Any, a1: Ctl) -> None:
        """A12: a restarted worker that applied nothing is not shown as running the old
        revision, and a heartbeat cannot claim a revision that was never delivered."""
        cam, _, scoped, _ = live_camera
        cfg = worker_get(scoped, "/api/ingest/cameras/e2e-replay/config").json()
        heartbeat(scoped, "e2e-replay", worker_epoch="epoch-first")
        ack(
            scoped,
            "e2e-replay",
            worker_epoch="epoch-first",
            revision=1,
            fingerprint=cfg["fingerprint"],
            status="accepted",
        )
        heartbeat(scoped, "e2e-replay", worker_epoch="epoch-first", seq=2, applied_revision=99)
        assert a1.detail(cam)["runtime"]["applied_revision"] == 1
        heartbeat(scoped, "e2e-replay", worker_epoch="epoch-first", seq=3, health="stopped")
        heartbeat(scoped, "e2e-replay", worker_epoch="epoch-second", seq=1)
        rt = a1.detail(cam)["runtime"]
        assert rt["applied_revision"] is None and rt["revision_in_sync"] is False
        heartbeat(scoped, "e2e-replay", worker_epoch="epoch-second", seq=2, applied_revision=1)
        rt = a1.detail(cam)["runtime"]
        assert rt["applied_revision"] == 1 and rt["revision_in_sync"] is True

    def test_old_sequence_does_not_overwrite(self, live_camera: Any, a1: Ctl) -> None:
        cam, _, scoped, _ = live_camera
        heartbeat(scoped, "e2e-replay", seq=10, processing_fps=10)
        r = heartbeat(scoped, "e2e-replay", seq=9, processing_fps=1).json()
        assert r["reason"] == "stale_sequence"
        assert a1.detail(cam)["worker"]["processing_fps"] == 10

    def test_legacy_heartbeat_unchanged_and_bad_body_refused(self, live_camera: Any) -> None:
        _, _, scoped, _ = live_camera
        target = "/api/ingest/cameras/e2e-replay/heartbeat"
        assert scoped.post(target, b"").status_code == 204
        assert scoped.post(target, b'{"worker_epoch": "x"}').status_code == 422

    def test_recordings_need_media_scope(self, live_camera: Any, a1: Ctl) -> None:
        cam, _, scoped, _ = live_camera
        r = send(
            scoped,
            "PUT",
            "/api/ingest/cameras/e2e-replay/video",
            files={"video": ("v.mp4", MP4, "video/mp4")},
        )
        assert r.status_code == 403
        assert r.json()["detail"]["reason"] == "recordings_not_authorized"
        a1.grant(cam, media_scope="events_and_recordings")
        r = send(
            scoped,
            "PUT",
            "/api/ingest/cameras/e2e-replay/video",
            files={"video": ("v.mp4", MP4, "video/mp4")},
        )
        assert r.status_code == 204, r.text

    def test_history_is_capped_and_survives_restart(
        self, live_camera: Any, a1: Ctl, world: World, login: Any, monkeypatch: Any
    ) -> None:
        """A17: status lives in PostgreSQL (a new app instance sees it); history is bounded."""
        monkeypatch.setattr(ctl, "HEALTH_HISTORY_CAP", 5)
        cam, _, scoped, _ = live_camera
        for seq in range(1, 9):
            heartbeat(
                scoped, "e2e-replay", seq=seq, health="healthy" if seq % 2 else "reconnecting"
            )
        fresh = Ctl(login(world.a.admin))  # a brand-new app instance
        events = fresh.c.get(f"{BASE}/{cam}/health", params={"limit": 50}).json()
        assert len(events) == 5
        assert fresh.detail(cam)["worker"]["seq"] == 8
        with admin_conn() as conn:
            assert (
                conn.execute(
                    "SELECT count(*) FROM camera_health_events WHERE camera_id = %s", (cam,)
                ).fetchone()[0]
                == 5
            )


# --------------------------------------------------------------------------- secrets


class TestSecrets:
    def test_source_credentials_never_leak(
        self, world: World, a1: Ctl, a2: Ctl, login: Any, caplog: Any
    ) -> None:
        """A16: responses, audit rows, health history, logs and errors never contain the
        credential, path or query of the source URL; the DB holds only ciphertext."""
        caplog.set_level(logging.DEBUG)
        cam = a1.create_camera("secret-cam")["id"]
        r = a1.source(cam, SECRET_URL, "authorized_network_live")
        assert r.status_code == 200
        assert r.json()["source_display"] == "rtsps://cam.example.org:8554"
        assert r.json()["source_has_credentials"] is True
        bad = a1.c.post(
            f"{BASE}/{cam}/source",
            {
                "kind": "authorized_network_live",
                "expected_revision": a1.rev(cam),
                "reason": "typo",
                "url": SECRET_URL.replace("rtsps", "http"),
            },
        )
        assert bad.status_code == 422
        a1.grant(cam, capture_method="authorized_network_live")
        vid = approved_version(a1, a2, cam)
        a1.activate(cam, vid)
        op = login(world.a.operator)
        texts = [
            r.text,
            bad.text,
            a1.c.get(f"{BASE}/{cam}").text,
            a1.c.get(BASE).text,
            op.get(f"{BASE}/{cam}").text,
            a1.c.get(f"{BASE}/{cam}/health").text,
            a1.c.get("/api/cameras").text,
            a1.c.get(f"/api/cameras/{cam}").text,
            json.dumps(audit_rows(world.a.id)),
            caplog.text,
        ]
        for text in texts:
            assert not any(m in text for m in SECRET_MARKERS), text[:400]
        with admin_conn() as conn:
            row = conn.execute(
                "SELECT source_url_enc, source_display FROM cameras WHERE id = %s", (cam,)
            ).fetchone()
        assert b"S3cr3tPass" not in bytes(row[0]) and row[1] == "rtsps://cam.example.org:8554"


# --------------------------------------------------------------------------- editor catalogue


def test_the_catalogue_states_exactly_what_the_validator_enforces(a1: Ctl, client: Any) -> None:
    """The editor builds its forms from this answer, so it cannot drift from the validator."""
    r = a1.c.get("/api/camera-control/catalog")
    assert r.status_code == 200, r.text
    cat = r.json()
    assert cat["schema_version"] == cc.SCHEMA_VERSION
    assert cat["coordinate_convention"] == "pixels_top_left"
    assert cat["zone_kinds"] == list(cc.ZONE_KINDS)
    assert {x["id"] for x in cat["rules"]} == set(cc.RULES)
    wrong_way = next(x for x in cat["rules"] if x["id"] == "wrong_way")
    assert wrong_way == {
        "id": "wrong_way",
        "needs_calibration": True,
        "min_fps": 10.0,
        "zone_kinds": ["carriageway", "emergency_lane"],
        "needs_direction": True,
    }
    limit = next(x for x in cat["thresholds"] if x["id"] == "speed_limit_kmh")
    assert limit == {
        "id": "speed_limit_kmh",
        "min": 5,
        "max": 200,
        "integer": False,
        "required": True,
        "default": 50,
    }
    # The offered starting values are themselves valid: a config built from them passes.
    built = config()
    built["thresholds"] = {x["id"]: x["default"] for x in cat["thresholds"] if x["required"]}
    built["acquisition"] = {x["id"]: x["default"] for x in cat["acquisition"]}
    assert [e.path for e in cc.validate(built) if e.path.startswith(("thresholds", "acquis"))] == []
    assert all(x["default"] is None for x in cat["thresholds"] if not x["required"])
    assert {x["id"] for x in cat["thresholds"] if x["required"]} == set(cc.REQUIRED_THRESHOLDS)
    optional = {x["id"] for x in cat["thresholds"] if not x["required"]}
    assert optional == set(cc.OPTIONAL_THRESHOLDS)
    assert next(x for x in cat["acquisition"] if x["id"] == "target_fps")["max"] == 60
    assert cat["limits"] == {"zones": 32, "polygon_points": 64, "frame_min": 64, "frame_max": 8192}
    # Every rule the catalogue lists is one the validator knows: none is reported as unknown.
    built = config()
    built["rules"] = [x["id"] for x in cat["rules"]]
    assert "unknown_rule" not in {e.code for e in cc.validate(built)}
    assert client.get("/api/camera-control/catalog").status_code == 401
