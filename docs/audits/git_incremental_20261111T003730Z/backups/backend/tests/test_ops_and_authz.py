"""Readiness, metrics, ops status; and a route-by-role authorization matrix over the whole API."""

from __future__ import annotations

import re
import uuid
from typing import Any

import pytest

from app.db import tenant_session
from app.models import Camera
from tests.conftest import ApiClient, World


class TestOps:
    def test_ready_reports_the_schema_version(self, client: ApiClient) -> None:
        r = client.get("/api/ready")
        assert r.status_code == 200 and r.json()["status"] == "ready" and r.json()["schema"]

    def test_metrics_are_off_without_a_token_and_need_it_with_one(
        self, client: ApiClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.config import get_settings

        assert client.get("/api/metrics").status_code == 404
        monkeypatch.setenv("RS_METRICS_TOKEN", "m" * 40)
        get_settings.cache_clear()
        try:
            assert client.get("/api/metrics").status_code == 401
            assert (
                client.get("/api/metrics", headers={"Authorization": "Bearer wrong"}).status_code
                == 401
            )
            client.get("/api/health")
            r = client.get("/api/metrics", headers={"Authorization": "Bearer " + "m" * 40})
            assert r.status_code == 200 and "rs_http_requests_total" in r.text
            assert "text/plain" in r.headers["content-type"]
        finally:
            monkeypatch.undo()
            get_settings.cache_clear()

    def test_ops_status_is_per_tenant_and_flags_stale_cameras(
        self, world: World, login: Any
    ) -> None:
        with tenant_session(world.a.id) as db:
            cam = db.get(Camera, world.data["a"]["camera"])
            cam.last_seen_at = None
            cam.status_info = {
                "fps": 0.5,
                "rules": {"hard_braking": {"supported": False, "min_fps": 7}},
            }
            db.commit()
        s = login(world.a.admin).get("/api/ops/status").json()
        assert (
            s["alerts_24h"] == 3 and s["new_unreviewed"] == 3 and s["cameras"][0]["stale"] is True
        )
        assert (
            s["cameras"][0]["unsupported_rules"] == ["hard_braking"]
            and s["cameras"][0]["fps"] == 0.5
        )
        assert any("never seen" in x for x in s["alerts_that_need_attention"])
        for user in (world.a.operator, world.a.patrol, world.a.auditor):
            assert login(user).get("/api/ops/status").status_code == 403

    def test_metrics_registry_renders_histograms_and_counters(self) -> None:
        from app.core.metrics import Registry

        r = Registry()
        r.inc("rs_x_total", result="ok")
        r.observe("rs_lat_seconds", 0.03)
        r.observe("rs_lat_seconds", 3.0)
        text = r.render()
        assert 'rs_x_total{result="ok"} 1' in text
        assert 'rs_lat_seconds_bucket{le="0.05"} 1' in text and "rs_lat_seconds_count 2" in text


# ----------------------------------------------------------------------------- authorization matrix
PUBLIC = {
    ("GET", "/api/docs"),
    ("GET", "/api/me"),  # by contract: anonymous -> {"operator": null, "auth_required": true}
    ("GET", "/api/openapi.json"),  # dev/test only: disabled when RS_ENV=production (main.py)
    ("GET", "/api/health"),
    ("GET", "/api/health/live"),
    ("GET", "/api/health/ready"),
    ("GET", "/api/ready"),
    ("GET", "/api/metrics"),
    ("GET", "/api/auth/csrf"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/refresh"),
    ("POST", "/api/login"),
    ("POST", "/api/auth/mfa/verify"),
    ("POST", "/api/auth/mfa/enroll/start"),
    ("POST", "/api/auth/mfa/enroll/confirm"),
    ("POST", "/api/auth/invitations/inspect"),
    ("POST", "/api/auth/invitations/accept"),
    ("POST", "/api/auth/reset/inspect"),
    ("POST", "/api/auth/reset/accept"),
    ("POST", "/api/logout"),
}
MACHINE = "/api/ingest"  # authenticated by HMAC signature, tested in test_ingest_auth.py


def concrete(path: str) -> str:
    u = str(uuid.uuid4())
    return re.sub(
        r"\{(number|id)\}",
        "1",
        re.sub(r"\{[^}]*_id\}|\{id\}|\{request_id\}|\{approval_id\}", u, path),
    )


def _walk(routes: Any) -> Any:
    """Newer FastAPI wraps included routers lazily (_IncludedRouter): descend into them."""
    for r in routes:
        inner = getattr(r, "original_router", None)
        if inner is not None:
            yield from _walk(inner.routes)
        else:
            yield r


def all_routes() -> list[tuple[str, str]]:
    from app.main import create_app

    app = create_app()
    out = []
    for r in _walk(app.routes):
        path = getattr(r, "path", "")
        if not path.startswith("/api") or path.startswith(MACHINE):
            continue
        for m in getattr(r, "methods", set()) - {"HEAD", "OPTIONS"}:
            out.append((m, path))
    routes = sorted(set(out))
    assert len(routes) > 60, f"route discovery is broken ({len(routes)} found)"
    return routes


def test_every_route_rejects_an_anonymous_caller_unless_listed_public(client: ApiClient) -> None:
    leaks = []
    for method, path in all_routes():
        if (method, path) in PUBLIC:
            continue
        r = client.http.request(
            method,
            concrete(path),
            json={} if method != "GET" else None,
            headers={"Origin": "https://testserver", "X-CSRF-Token": client.csrf},
        )
        if r.status_code not in (401, 403, 404, 405, 422):
            leaks.append((method, path, r.status_code))
        if r.status_code == 200:
            leaks.append((method, path, "200 without a session"))
    assert not leaks, f"routes answer anonymous callers: {leaks}"


# who may NOT call what (role -> [(method, path template)]): every one must be 403 (or 404 when the
# resource would not be visible to that role). Allowed roles are covered by the feature tests.
FORBIDDEN: dict[str, list[tuple[str, str]]] = {
    "patrol": [
        ("GET", "/api/users"),
        ("POST", "/api/users/invitations"),
        ("GET", "/api/retention"),
        ("POST", "/api/retention/purge"),
        ("GET", "/api/audit/chain"),
        ("GET", "/api/ops/status"),
        ("POST", "/api/cameras"),
        ("GET", "/api/service-accounts"),
        ("GET", "/api/patrols"),
        ("GET", "/api/stats/response"),
        ("POST", "/api/approvals/{id}/approve"),
    ],
    "auditor": [
        ("GET", "/api/alerts"),
        ("GET", "/api/users"),
        ("POST", "/api/alerts/{id}/confirm"),
        ("GET", "/api/retention"),
        ("GET", "/api/patrols"),
        ("GET", "/api/stats/response"),
        ("GET", "/api/cameras/{id}"),
        ("POST", "/api/approvals"),
        ("GET", "/api/evidence"),
    ],
    "operator": [
        ("GET", "/api/users"),
        ("POST", "/api/users/invitations"),
        ("GET", "/api/retention"),
        ("PUT", "/api/retention"),
        ("POST", "/api/cameras"),
        ("PATCH", "/api/cameras/{id}"),
        ("GET", "/api/service-accounts"),
        ("POST", "/api/tenants"),
        ("GET", "/api/ops/status"),
        ("POST", "/api/approvals/{id}/approve"),
        ("POST", "/api/approvals/{id}/deny"),
        ("GET", "/api/audit/chain"),
        ("POST", "/api/users/{id}/reset-requests"),
    ],
    "tenant_admin": [("POST", "/api/tenants"), ("POST", "/api/alerts/{id}/patrol-status")],
}


@pytest.mark.parametrize("role", sorted(FORBIDDEN))
def test_forbidden_matrix(world: World, login: Any, role: str) -> None:
    user = {
        "patrol": world.a.patrol,
        "auditor": world.a.auditor,
        "operator": world.a.operator,
        "tenant_admin": world.a.admin,
    }[role]
    c = login(user)
    wrong = []
    for method, tpl in FORBIDDEN[role]:
        path = tpl.replace("{id}", str(world.data["a"]["alerts"][0]))
        r = c.http.request(
            method,
            path,
            json={} if method != "GET" else None,
            headers={"Origin": "https://testserver", "X-CSRF-Token": c.csrf},
        )
        bad_422 = r.status_code == 422 and role != "tenant_admin"
        if r.status_code not in (403, 404, 422) or bad_422:
            wrong.append((method, tpl, r.status_code))
    assert not wrong, f"{role} reached routes it must not: {wrong}"


def test_cross_tenant_ids_are_invisible_everywhere(world: World, login: Any) -> None:
    """Unit A's admin and operator use unit B's ids on id-taking routes: never data, never 200."""
    b_alert, b_cam, b_ev = (
        str(world.data["b"][k]) for k in ("assigned_alert", "camera", "evidence")
    )
    for user in (world.a.admin, world.a.operator):
        c = login(user)
        probes = [
            ("GET", f"/api/alerts/{b_alert}"),
            ("POST", f"/api/alerts/{b_alert}/confirm"),
            ("POST", f"/api/alerts/{b_alert}/assign"),
            ("GET", f"/api/cameras/{b_cam}"),
            ("GET", f"/api/evidence/{b_ev}"),
            ("POST", f"/api/evidence/{b_ev}/access"),
            ("POST", f"/api/alerts/{b_alert}/patrol-status"),
            ("POST", f"/api/retention/holds/{b_alert}"),
            ("PATCH", f"/api/cameras/{b_cam}"),
        ]
        for method, path in probes:
            r = c.http.request(
                method,
                path,
                json={
                    "variant": "redacted",
                    "reason": "x" * 20,
                    "status": "done",
                    "user_id": str(uuid.uuid4()),
                    "name": "zz",
                },
                headers={"Origin": "https://testserver", "X-CSRF-Token": c.csrf},
            )
            assert r.status_code in (403, 404, 422), (user.role, method, path, r.status_code)
            assert str(world.data["b"]["plates"][0]) not in r.text


GARBAGE: list[Any] = [
    {},
    [],
    None,
    "x" * 70000,
    {"a": {"b": {"c": {"d": {"e": [1] * 500}}}}},
    {"id": "../../etc/passwd", "user_id": "not-a-uuid", "status": 5, "days": {"clip": "NaN"}},
    {
        "email": "a" * 400 + "@x.co",
        "password": "\u0000" * 50,
        "token": "💥" * 40,
        "code": "' OR 1=1 --",
    },
    {"justification": "ü" * 3000, "case_reference": "\n" * 200, "reason": "x" * 600},
]


def test_garbage_input_never_causes_a_server_error(world: World, login: Any) -> None:
    """Every state-changing, cookie-authenticated route, called as a tenant admin with hostile
    bodies: the answer may be a refusal, never a 5xx and never a stack trace."""
    admin = login(world.a.admin)
    a_alert = str(world.data["a"]["alerts"][0])
    bad = []
    sent = 0
    for method, path in all_routes():
        if (
            method == "GET"
            or (method, path) in PUBLIC
            or path in ("/api/logout", "/api/auth/logout")
        ):
            continue
        url = path
        for token in (
            "{alert_id}",
            "{id}",
            "{approval_id}",
            "{request_id}",
            "{user_id}",
            "{camera_id}",
            "{evidence_id}",
            "{invitation_id}",
            "{account_id}",
            "{key_id}",
            "{session_id}",
            "{number}",
        ):
            url = url.replace(token, a_alert if token != "{number}" else "1")
        for body in GARBAGE:
            r = admin.http.request(
                method,
                url,
                json=body,
                headers={"Origin": "https://testserver", "X-CSRF-Token": admin.csrf},
            )
            sent += 1
            if r.status_code >= 500 or "Traceback" in r.text:
                bad.append((method, path, r.status_code, str(body)[:30]))
    assert sent > 200, f"only {sent} hostile requests were sent: the route walk is broken"
    assert not bad, f"server errors on hostile input: {bad[:10]}"


def test_me_reveals_nothing_to_an_anonymous_caller(client: ApiClient) -> None:
    body = client.get("/api/me").json()
    assert body["operator"] is None and body["auth_required"] is True
    assert set(body) <= {"operator", "auth_required", "mfa_required", "mfa_enrollment"}
