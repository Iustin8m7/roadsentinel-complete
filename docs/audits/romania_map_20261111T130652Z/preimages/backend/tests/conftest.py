"""Test fixtures. Tests run against a real PostgreSQL 16 (RLS, roles and triggers cannot be
faked). Point ``RS_TEST_ADMIN_DATABASE_URL`` at a superuser connection; a throwaway database
``rs_test`` is (re)created for the session.
"""

from __future__ import annotations

import base64
import os
import secrets
import tempfile
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import pyotp
import pytest
from sqlalchemy.engine import make_url

ADMIN_URL = os.environ.get(
    "RS_TEST_ADMIN_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
)
TEST_DB = os.environ.get("RS_TEST_DATABASE_NAME", "rs_test")
if not __import__("re").fullmatch(r"rsmission_[a-z0-9_]+|rs_test", TEST_DB):
    raise RuntimeError("Invalid disposable test database name")
_owner_pw, _app_pw = secrets.token_urlsafe(16), secrets.token_urlsafe(16)
_base = make_url(ADMIN_URL)
MIGRATOR_URL = _base.set(
    username="rs_test_owner", password=_owner_pw, database=TEST_DB
).render_as_string(hide_password=False)
APP_URL = _base.set(username="rs_test_app", password=_app_pw, database=TEST_DB).render_as_string(
    hide_password=False
)
TEST_ADMIN_URL = _base.set(database=TEST_DB).render_as_string(hide_password=False)
EVIDENCE_DIR = Path(tempfile.mkdtemp(prefix="rs-evidence-"))
ORIGIN = "https://testserver"

os.environ.update(
    {
        "RS_ENV": "test",
        "RS_DATABASE_URL": APP_URL,
        "RS_MIGRATOR_DATABASE_URL": MIGRATOR_URL,
        "RS_ADMIN_DATABASE_URL": ADMIN_URL,
        "RS_JWT_SECRET": secrets.token_urlsafe(48),
        "RS_URL_SIGNING_KEY": secrets.token_urlsafe(48),
        "RS_MASTER_KEYS": "1:" + base64.b64encode(secrets.token_bytes(32)).decode(),
        "RS_MASTER_KEY_CURRENT": "1",
        "RS_EVIDENCE_DIR": str(EVIDENCE_DIR),
        "RS_PUBLIC_ORIGIN": ORIGIN,
        "RS_COOKIE_SECURE": "true",
        "RS_ARGON2_TIME_COST": "1",
        "RS_ARGON2_MEMORY_COST_KIB": "1024",
        "RS_ARGON2_PARALLELISM": "1",
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from app.core.http import CSRF, CSRF_HEADER, cookie_name  # noqa: E402
from app.core.rate_limit import get_rate_limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db import tenant_session  # noqa: E402
from app.models import TENANT_SCOPED_TABLES, Role, User  # noqa: E402

PASSWORD = "Correct-Horse-Battery-42"


def _plain(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def admin_conn() -> psycopg.Connection[Any]:
    """Superuser connection to the test database (the 'privileged attacker' in tamper tests)."""
    return psycopg.connect(_plain(TEST_ADMIN_URL), autocommit=True)


def app_conn() -> psycopg.Connection[Any]:
    """Raw connection with the restricted app role, for direct-SQL isolation tests."""
    return psycopg.connect(_plain(APP_URL))


@pytest.fixture(scope="session", autouse=True)
def database() -> Iterator[None]:
    with psycopg.connect(_plain(ADMIN_URL), autocommit=True) as conn:
        identity = conn.execute(
            "SELECT current_database(), host(inet_server_addr()), inet_server_port(), current_user"
        ).fetchone()
        if os.environ.get("RS_TEST_ALLOW_DATABASE_RESET") != TEST_DB:
            raise RuntimeError(
                "Set RS_TEST_ALLOW_DATABASE_RESET to the exact disposable test DB name"
            )
        if str(identity[2]) != os.environ.get("RS_TEST_EXPECTED_PORT"):
            raise RuntimeError("Disposable PostgreSQL port identity mismatch")
        print("Disposable test PostgreSQL identity:", identity, "target:", TEST_DB)
        conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
    from alembic.config import Config

    from alembic import command
    from app.bootstrap import bootstrap

    bootstrap(ADMIN_URL, MIGRATOR_URL, APP_URL)
    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    command.upgrade(cfg, "head")
    yield
    from app.db import get_engine

    get_engine().dispose()


@pytest.fixture(autouse=True)
def clean(database: None) -> Iterator[None]:
    get_rate_limiter().reset()
    yield
    tables = ", ".join(("tenants", *TENANT_SCOPED_TABLES))
    with admin_conn() as conn:
        conn.execute("SET session_replication_role = replica")  # bypass audit triggers
        conn.execute(f"TRUNCATE {tables} CASCADE")


# --------------------------------------------------------------------------- world


@dataclass
class TUser:
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: Role
    totp_secret: str | None = field(repr=False)
    password: str = field(default=PASSWORD, repr=False)

    def totp(self) -> str:
        assert self.totp_secret
        reset_totp_step(self.id)
        return pyotp.TOTP(self.totp_secret).now()


@dataclass
class Unit:
    id: uuid.UUID
    users: dict[Role, TUser] = field(default_factory=dict)

    @property
    def admin(self) -> TUser:
        return self.users[Role.tenant_admin]

    @property
    def operator(self) -> TUser:
        return self.users[Role.operator]

    @property
    def patrol(self) -> TUser:
        return self.users[Role.patrol]

    @property
    def auditor(self) -> TUser:
        return self.users[Role.auditor]


def reset_totp_step(user_id: uuid.UUID) -> None:
    with admin_conn() as conn:
        conn.execute("UPDATE users SET totp_last_step = NULL WHERE id = %s", (user_id,))


def make_user(
    tenant_id: uuid.UUID, role: Role, email: str, *, mfa: bool = True, password: str = PASSWORD
) -> TUser:
    from app.core.crypto import encrypt_field
    from app.services.keys import load_keyring

    secret = pyotp.random_base32(32) if mfa else None
    with tenant_session(tenant_id) as db:
        user = User(
            tenant_id=tenant_id,
            email=email,
            display_name=email.split("@")[0],
            role=role,
            password_hash=hash_password(password),
            mfa_enabled=mfa,
        )
        if secret:
            user.totp_secret_enc = encrypt_field(
                load_keyring(db, tenant_id), "users.totp_secret", secret
            )
        db.add(user)
        db.commit()
        return TUser(user.id, tenant_id, email, role, secret, password)


@dataclass
class World:
    platform: Unit
    a: Unit
    b: Unit
    data: dict[str, Any] = field(default_factory=dict)


@pytest.fixture
def world() -> World:
    """Platform + Unit A + Unit B with one user per role, a camera, alerts and evidence."""
    from app.core.crypto import blind_index, encrypt_field, normalize_plate
    from app.models import Alert, Camera, Priority
    from app.services import evidence as evidence_service
    from app.services.keys import load_keyring
    from app.services.seed import make_png
    from app.services.tenants import create_tenant

    platform_id = create_tenant("Platform", "platform", is_platform=True)
    platform = Unit(platform_id)
    platform.users[Role.system_admin] = make_user(platform_id, Role.system_admin, "sys@test.local")
    w = World(
        platform=platform,
        a=Unit(create_tenant("Unit A", "unit-a")),
        b=Unit(create_tenant("Unit B", "unit-b")),
    )
    for letter, unit in (("a", w.a), ("b", w.b)):
        for role in (Role.tenant_admin, Role.operator, Role.patrol, Role.auditor):
            unit.users[role] = make_user(unit.id, role, f"{role.value}.{letter}@test.local")
        with tenant_session(unit.id) as db:
            kr = load_keyring(db, unit.id)
            cam = Camera(tenant_id=unit.id, name=f"cam-{letter}", location="km 1")
            db.add(cam)
            db.flush()
            alerts = []
            for i, prio in enumerate([Priority.info, Priority.critical, Priority.high]):
                plate = normalize_plate(f"{letter.upper()}{i}0XYZ")
                alert = Alert(
                    tenant_id=unit.id,
                    camera_id=cam.id,
                    priority=prio,
                    event_type="test_event",
                    description=f"alert {letter}{i}",
                    detected_at=datetime.now(UTC) - timedelta(minutes=i),
                    plate_enc=encrypt_field(kr, "alerts.plate", plate),
                    plate_bidx=blind_index(kr, "alerts.plate", plate),
                    assigned_to=unit.patrol.id if i == 1 else None,
                )
                db.add(alert)
                db.flush()
                alerts.append(alert)
            ev = evidence_service.ingest(
                db,
                kr,
                alerts[1],
                original=make_png(16, 12, redacted=False, seed=1),
                redacted=make_png(16, 12, redacted=True, seed=1),
                content_type="image/png",
            )
            db.commit()
            w.data[letter] = {
                "camera": cam.id,
                "alerts": [a.id for a in alerts],
                "assigned_alert": alerts[1].id,
                "evidence": ev.id,
                "plates": [normalize_plate(f"{letter.upper()}{i}0XYZ") for i in range(3)],
            }
    return w


# --------------------------------------------------------------------------- HTTP client


class ApiClient:
    """TestClient wrapper that behaves like the SPA: fetches a CSRF token and sends it back
    in the X-CSRF-Token header on every unsafe request."""

    def __init__(self) -> None:
        from app.main import create_app

        self.http = TestClient(create_app(), base_url=ORIGIN, raise_server_exceptions=False)
        self.http.get("/api/auth/csrf")

    @property
    def csrf(self) -> str:
        return self.http.cookies.get(cookie_name(CSRF), path="/") or ""

    def _headers(self, extra: dict[str, str] | None) -> dict[str, str]:
        return {CSRF_HEADER: self.csrf, "Origin": ORIGIN, **(extra or {})}

    def get(self, url: str, **kw: Any) -> Any:
        return self.http.get(url, **kw)

    def post(
        self, url: str, json: Any = None, headers: dict[str, str] | None = None, **kw: Any
    ) -> Any:
        return self.http.post(url, json=json, headers=self._headers(headers), **kw)

    def patch(
        self, url: str, json: Any = None, headers: dict[str, str] | None = None, **kw: Any
    ) -> Any:
        return self.http.patch(url, json=json, headers=self._headers(headers), **kw)

    def put(
        self, url: str, json: Any = None, headers: dict[str, str] | None = None, **kw: Any
    ) -> Any:
        return self.http.put(url, json=json, headers=self._headers(headers), **kw)

    def delete(self, url: str, headers: dict[str, str] | None = None, **kw: Any) -> Any:
        return self.http.delete(url, headers=self._headers(headers), **kw)

    def login(self, user: TUser) -> ApiClient:
        r = self.post("/api/auth/login", {"email": user.email, "password": user.password})
        assert r.status_code == 200, r.text
        r = self.post("/api/auth/mfa/verify", {"code": user.totp()})
        assert r.status_code == 204, r.text
        return self


@pytest.fixture
def client() -> ApiClient:
    return ApiClient()


@pytest.fixture
def login() -> Any:
    def _login(user: TUser) -> ApiClient:
        return ApiClient().login(user)

    return _login


def audit_actions(tenant_id: uuid.UUID) -> list[str]:
    with admin_conn() as conn:
        rows = conn.execute(
            "SELECT action FROM audit_log WHERE tenant_id = %s ORDER BY seq", (tenant_id,)
        ).fetchall()
    return [r[0] for r in rows]


def wait_for(predicate: Any, timeout: float = 2.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.02)
    return False
