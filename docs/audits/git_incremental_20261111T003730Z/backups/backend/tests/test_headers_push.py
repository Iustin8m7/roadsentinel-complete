"""HTTP hardening headers and the Web Push privacy guarantee."""

from __future__ import annotations

from typing import Any

import pytest

from app.models import Priority
from app.services.push import ALLOWED_PAYLOAD_KEYS, _assert_generic, build_alert_payload
from tests.conftest import ApiClient, World


class TestHeaders:
    @pytest.mark.parametrize("path", ["/api/health", "/api/auth/me", "/api/alerts", "/api/nope"])
    def test_security_headers_on_every_api_response(self, client: ApiClient, path: str) -> None:
        h = client.get(path).headers
        assert h["strict-transport-security"].startswith("max-age=63072000")
        assert h["x-content-type-options"] == "nosniff"
        assert h["referrer-policy"] == "no-referrer"
        assert h["cross-origin-opener-policy"] == "same-origin"
        assert h["cross-origin-resource-policy"] == "same-origin"
        assert "camera=()" in h["permissions-policy"]
        assert h["cache-control"] == "no-store"
        csp = h["content-security-policy"]
        assert (
            "frame-ancestors 'none'" in csp
            and "unsafe-inline" not in csp
            and "unsafe-eval" not in csp
        )

    def test_authenticated_responses_are_not_cacheable(self, world: World, login: Any) -> None:
        r = login(world.a.operator).get("/api/alerts")
        assert r.status_code == 200 and r.headers["cache-control"] == "no-store"

    def test_app_csp_has_no_unsafe_sources(self) -> None:
        from app.core.http import APP_CSP

        for directive in (
            "default-src 'self'",
            "frame-ancestors 'none'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ):
            assert directive in APP_CSP
        assert "unsafe" not in APP_CSP

    def test_caddy_sets_the_same_policy(self) -> None:
        from pathlib import Path

        caddy = (Path(__file__).resolve().parents[2] / "deploy" / "Caddyfile").read_text()
        assert "Strict-Transport-Security" in caddy and "unsafe-inline" not in caddy
        assert "frame-ancestors 'none'" in caddy

    def test_docs_disabled_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi.testclient import TestClient

        from app.config import get_settings
        from app.main import create_app

        monkeypatch.setattr(get_settings(), "env", "production")
        # Start-up safety is covered in test_startup.py; here we only check the docs routes.
        monkeypatch.setattr("app.main.enforce_production_safety", lambda *_: None)
        c = TestClient(create_app(), base_url="https://testserver")
        assert c.get("/api/docs").status_code == 404
        assert c.get("/api/openapi.json").status_code == 404


class TestPushPayload:
    @pytest.mark.parametrize("priority", list(Priority))
    def test_payload_is_generic(self, priority: Priority) -> None:
        payload = build_alert_payload(priority)
        assert set(payload) <= ALLOWED_PAYLOAD_KEYS
        assert payload["body"] == f"New alert, priority: {priority.value}"
        assert payload["title"] == "RoadSentinel"

    def test_non_generic_payload_rejected(self) -> None:
        with pytest.raises(ValueError):
            _assert_generic({"title": "x", "body": "y", "image": "https://..."})

    def test_subscription_requires_https_endpoint_and_is_tenant_scoped(
        self, world: World, login: Any
    ) -> None:
        c = login(world.a.operator)
        bad = c.post(
            "/api/push/subscriptions", {"endpoint": "http://evil", "p256dh": "k", "auth": "a"}
        )
        assert bad.status_code == 422
        ok = c.post(
            "/api/push/subscriptions",
            {"endpoint": "https://push.example/abc", "p256dh": "k", "auth": "a"},
        )
        assert ok.status_code == 204
        assert c.delete("/api/push/subscriptions").status_code == 204
