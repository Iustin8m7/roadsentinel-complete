"""P0.1: production start-up safety, configuration hardening and generic errors."""

from __future__ import annotations

import base64
import logging
import secrets
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine

from app.config import Settings, get_settings
from app.core.startup import (
    InsecureConfigurationError,
    config_problems,
    database_role_problems,
    enforce_production_safety,
)
from app.db import get_engine
from tests.conftest import ADMIN_URL, APP_URL, MIGRATOR_URL, ORIGIN


def good(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "env": "production",
        "debug": False,
        "cors_origins": "",
        "database_url": SecretStr(APP_URL),
        "jwt_secret": SecretStr(secrets.token_urlsafe(48)),
        "url_signing_key": SecretStr(secrets.token_urlsafe(48)),
        "master_keys": SecretStr("1:" + base64.b64encode(secrets.token_bytes(32)).decode()),
        "public_origin": "https://rs.example.police",
        "cookie_secure": True,
        "seed_password": None,
        "admin_database_url": None,
        "migrator_database_url": None,
    }
    values.update(overrides)
    return Settings.model_construct(**values)


class TestEnvParsing:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("dev", "development"), ("prod", "production"), ("PROD", "production"), ("test", "test")],
    )
    def test_app_env_aliases(
        self, raw: str, expected: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("RS_ENV", raising=False)
        monkeypatch.setenv("APP_ENV", raw)
        assert Settings().env == expected  # type: ignore[call-arg]

    def test_unknown_env_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RS_ENV", "staging-ish")
        with pytest.raises(ValueError):
            Settings()  # type: ignore[call-arg]

    def test_default_is_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("RS_ENV", raising=False)
        monkeypatch.delenv("APP_ENV", raising=False)
        assert Settings().is_production  # type: ignore[call-arg]


WEAK_CASES = [
    ({"jwt_secret": SecretStr("")}, "RS_JWT_SECRET is missing"),
    ({"jwt_secret": SecretStr("short-secret")}, "shorter than"),
    ({"jwt_secret": SecretStr("changeme")}, "known default"),
    ({"jwt_secret": SecretStr("__GENERATE__")}, "known default"),
    ({"jwt_secret": SecretStr("a" * 64)}, "entropy"),
    ({"url_signing_key": SecretStr("secret")}, "RS_URL_SIGNING_KEY"),
    ({"master_keys": SecretStr("")}, "RS_MASTER_KEYS is missing"),
    ({"master_keys": SecretStr("1:" + base64.b64encode(bytes(32)).decode())}, "weak key"),
    ({"master_keys": SecretStr("1:" + base64.b64encode(b"short").decode())}, "32 bytes"),
    ({"master_keys": SecretStr("1:not base64!!")}, "invalid key"),
    ({"debug": True}, "RS_DEBUG"),
    ({"cookie_secure": False}, "RS_COOKIE_SECURE"),
    ({"public_origin": "http://rs.example.police"}, "RS_PUBLIC_ORIGIN"),
    ({"cors_origins": "*"}, "wildcard"),
    ({"cors_origins": "https://ok.example,http://plain.example"}, "https origins"),
    ({"seed_password": SecretStr("Dev-xyz")}, "RS_SEED_PASSWORD"),
    ({"admin_database_url": SecretStr(ADMIN_URL)}, "superuser"),
]


class TestProductionConfig:
    def test_good_config_passes(self) -> None:
        assert config_problems(good()) == []

    @pytest.mark.parametrize(("overrides", "fragment"), WEAK_CASES)
    def test_each_failure_mode(self, overrides: dict[str, Any], fragment: str) -> None:
        problems = config_problems(good(**overrides))
        assert any(fragment in p for p in problems), problems

    def test_same_secret_for_jwt_and_urls_rejected(self) -> None:
        s = SecretStr(secrets.token_urlsafe(48))
        problems = config_problems(good(jwt_secret=s, url_signing_key=s))
        assert any("must differ" in p for p in problems)

    def test_problems_never_contain_secret_values(self) -> None:
        weak = "changeme-but-long-enough-to-pass-length-check"
        problems = config_problems(good(jwt_secret=SecretStr(weak)))
        assert problems and not any(weak in p for p in problems)


class TestDatabaseRoleCheck:
    def test_restricted_app_role_passes(self) -> None:
        assert database_role_problems(get_engine()) == []

    def test_superuser_role_rejected(self) -> None:
        engine = create_engine(ADMIN_URL)
        try:
            problems = database_role_problems(engine)
        finally:
            engine.dispose()
        assert "database role is a superuser" in problems
        assert "database role has BYPASSRLS" in problems

    def test_owner_role_rejected(self) -> None:
        engine = create_engine(MIGRATOR_URL)
        try:
            problems = database_role_problems(engine)
        finally:
            engine.dispose()
        assert any("BYPASSRLS" in p for p in problems)
        assert any("owns tables" in p for p in problems)

    def test_enforce_raises_in_prod_and_skips_in_dev(self) -> None:
        with pytest.raises(InsecureConfigurationError):
            enforce_production_safety(good(debug=True), get_engine())
        enforce_production_safety(good(), get_engine())  # restricted role + good config
        enforce_production_safety(good(env="development", debug=True), get_engine())

    def test_superuser_connection_refused_in_prod(self) -> None:
        engine = create_engine(ADMIN_URL)
        try:
            with pytest.raises(InsecureConfigurationError, match="superuser"):
                enforce_production_safety(good(), engine)
        finally:
            engine.dispose()

    def test_app_factory_refuses_to_start(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.main import create_app

        # Test settings carry a superuser URL (RS_ADMIN_DATABASE_URL): must refuse in prod.
        monkeypatch.setattr(get_settings(), "env", "production")
        with pytest.raises(InsecureConfigurationError):
            create_app()


class TestGenericErrors:
    def test_500_hides_internals_and_returns_correlation_id(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        from app.main import create_app

        app = create_app()

        def boom() -> None:
            raise RuntimeError(
                "psycopg.errors.UndefinedTable: SELECT * FROM secret_table at C:/srv/app/db.py"
            )

        app.add_api_route("/api/__boom", boom)
        client = TestClient(app, base_url=ORIGIN, raise_server_exceptions=False)
        with caplog.at_level(logging.ERROR):
            r = client.get("/api/__boom")
        assert r.status_code == 500
        body = r.json()
        assert body["detail"] == "Internal server error" and len(body["correlation_id"]) == 32
        for leak in ("secret_table", "psycopg", "db.py", "Traceback", "RuntimeError"):
            assert leak not in r.text
        assert r.headers["x-request-id"] == body["correlation_id"]
        assert r.headers["cache-control"] == "no-store"
        record = next(rec for rec in caplog.records if rec.getMessage() == "unhandled error")
        assert getattr(record, "correlation_id", None) == body["correlation_id"]
        assert record.exc_info is not None

    def test_404_is_generic(self, client: Any) -> None:
        assert client.get("/api/does-not-exist").json() == {"detail": "Not Found"}


class TestCors:
    def test_no_cors_headers_by_default(self, client: Any) -> None:
        r = client.http.get("/api/health", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in r.headers

    def test_allowlisted_origin_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.main import create_app

        monkeypatch.setattr(get_settings(), "cors_origins", "https://dispatch.example")
        c = TestClient(create_app(), base_url=ORIGIN)
        preflight = {"Access-Control-Request-Method": "GET"}
        ok = c.options("/api/alerts", headers={"Origin": "https://dispatch.example", **preflight})
        assert ok.headers.get("access-control-allow-origin") == "https://dispatch.example"
        bad = c.options("/api/alerts", headers={"Origin": "https://evil.example", **preflight})
        assert "access-control-allow-origin" not in bad.headers


def test_production_refuses_mfa_exemption() -> None:
    assert any("MFA_EXEMPTION" in p for p in config_problems(good(mfa_exemption_enabled=True)))


class TestEvidenceStorageWarnings:
    def test_tmp_is_flagged_as_ephemeral(self) -> None:
        from pathlib import Path

        from app.core.startup import evidence_storage_warnings

        w = evidence_storage_warnings(good(evidence_dir=Path("/tmp/rs-evidence")))
        assert w and "DELETES" in w[0]

    def test_s3_bucket_means_no_warning(self) -> None:
        from pathlib import Path

        from app.core.startup import evidence_storage_warnings

        s = good(evidence_dir=Path("/tmp/x"), evidence_s3_bucket="b")
        assert evidence_storage_warnings(s) == []

    def test_production_local_disk_warns_to_use_a_volume(self) -> None:
        from pathlib import Path

        from app.core.startup import evidence_storage_warnings

        assert evidence_storage_warnings(good(evidence_dir=Path("/data/evidence")))
