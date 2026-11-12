"""Tenant isolation, proven at both layers: the API (Unit B can't touch Unit A through any
endpoint, and gets 404 rather than 403) and the database (RLS with the app role)."""

from __future__ import annotations

import uuid
from typing import Any

import psycopg
import pytest

from app.models import TENANT_SCOPED_TABLES
from tests.conftest import ApiClient, World, admin_conn, app_conn, audit_actions


def _a_ids(world: World) -> dict[str, Any]:
    d = world.data["a"]
    return {
        "alert": d["alerts"][0],
        "camera": d["camera"],
        "evidence": d["evidence"],
        "user": world.a.operator.id,
        "admin": world.a.admin.id,
    }


def _cross_tenant_requests(
    world: World, approval_id: uuid.UUID, session_id: str
) -> list[tuple[str, str, Any]]:
    a = _a_ids(world)
    return [
        ("get", f"/api/alerts/{a['alert']}", None),
        ("post", f"/api/alerts/{a['alert']}/confirm", None),
        ("post", f"/api/alerts/{a['alert']}/reject", None),
        ("post", f"/api/alerts/{a['alert']}/assign", {"user_id": str(world.b.patrol.id)}),
        ("get", f"/api/cameras/{a['camera']}", None),
        ("get", f"/api/evidence/{a['evidence']}", None),
        ("get", f"/api/evidence?alert_id={a['alert']}", None),
        ("post", f"/api/evidence/{a['evidence']}/access", {"variant": "redacted"}),
        ("post", f"/api/evidence/{a['evidence']}/export", None),
        (
            "post",
            "/api/approvals",
            {
                "evidence_id": str(a["evidence"]),
                "justification": "x" * 25,
                "case_reference": "CASE-1",
            },
        ),
        ("get", f"/api/approvals/{approval_id}", None),
        ("post", f"/api/approvals/{approval_id}/approve", None),
        ("post", f"/api/approvals/{approval_id}/deny", None),
        ("post", f"/api/approvals/{approval_id}/revoke", None),
        ("patch", f"/api/users/{a['user']}", {"is_active": False}),
        ("get", f"/api/users/{a['user']}/sessions", None),
        ("delete", f"/api/users/{a['user']}/sessions/{session_id}", None),
        ("delete", f"/api/sessions/{session_id}", None),
    ]


@pytest.fixture
def a_approval(world: World, login: Any) -> uuid.UUID:
    op = login(world.a.operator)
    r = op.post(
        "/api/approvals",
        {
            "evidence_id": str(world.data["a"]["evidence"]),
            "justification": "Needed for case file 42",
            "case_reference": "CASE-42",
        },
    )
    assert r.status_code == 201, r.text
    return uuid.UUID(r.json()["id"])


class TestApiIsolation:
    @pytest.mark.parametrize("attacker_role", ["tenant_admin", "operator"])
    def test_unit_b_cannot_touch_unit_a(
        self, world: World, login: Any, a_approval: uuid.UUID, attacker_role: str
    ) -> None:
        victim = login(world.a.operator)
        session_id = victim.get("/api/auth/me").json()["session_id"]
        attacker_user = world.b.admin if attacker_role == "tenant_admin" else world.b.operator
        b = login(attacker_user)
        failures = []
        for method, url, body in _cross_tenant_requests(world, a_approval, session_id):
            kwargs = {"json": body} if body is not None and method != "get" else {}
            r = getattr(b, method)(url, **kwargs)
            # A tenant admin holds every permission, so each lookup must be a plain 404. An
            # operator may get 403 only where its role lacks the permission altogether.
            allowed = {404} if attacker_role == "tenant_admin" else {404, 403}
            if r.status_code not in allowed or r.json().get("detail") == "reauth_required":
                failures.append((method, url, r.status_code, r.text[:120]))
        assert not failures, failures

        # Nothing of Unit A changed, and Unit A's session is still alive.
        assert victim.get("/api/auth/me").status_code == 200
        with admin_conn() as conn:
            status = conn.execute(
                "SELECT status FROM alerts WHERE id = %s", (world.data["a"]["alerts"][0],)
            ).fetchone()
            pending = conn.execute(
                "SELECT status FROM approval_requests WHERE id = %s", (a_approval,)
            ).fetchone()
            active = conn.execute(
                "SELECT is_active FROM users WHERE id = %s", (world.a.operator.id,)
            ).fetchone()
        assert status == ("new",) and pending == ("pending",) and active == (True,)

    def test_responses_identical_for_foreign_and_nonexistent(
        self, world: World, login: Any
    ) -> None:
        b = login(world.b.operator)
        foreign = b.get(f"/api/alerts/{world.data['a']['alerts'][0]}")
        missing = b.get(f"/api/alerts/{uuid.uuid4()}")
        assert foreign.status_code == missing.status_code == 404
        assert foreign.json() == missing.json()

    def test_cross_tenant_probe_is_audited_in_both_tenants(self, world: World, login: Any) -> None:
        b = login(world.b.operator)
        b.get(f"/api/alerts/{world.data['a']['alerts'][0]}")
        assert "security.cross_tenant_access" in audit_actions(world.b.id)
        assert "security.cross_tenant_access" in audit_actions(world.a.id)
        # A genuinely missing id is not reported as cross-tenant.
        before = audit_actions(world.b.id).count("security.cross_tenant_access")
        b.get(f"/api/alerts/{uuid.uuid4()}")
        assert audit_actions(world.b.id).count("security.cross_tenant_access") == before

    def test_lists_only_show_own_tenant(self, world: World, login: Any) -> None:
        b_admin = login(world.b.admin)
        a_alerts = {str(x) for x in world.data["a"]["alerts"]}
        listed = {x["id"] for x in b_admin.get("/api/alerts").json()}
        assert listed and not (listed & a_alerts)
        assert {c["uuid"] for c in b_admin.get("/api/cameras").json()} == {
            str(world.data["b"]["camera"])
        }
        emails = {u["email"] for u in b_admin.get("/api/users").json()}
        assert emails and all(e.endswith(".b@test.local") for e in emails)
        assert all(
            e["details"].get("actor_tenant_id", str(world.b.id)) == str(world.b.id)
            for e in login(world.b.auditor).get("/api/audit/chain").json()
        )

    def test_plate_search_does_not_cross_tenants(self, world: World, login: Any) -> None:
        a_plate = world.data["a"]["plates"][0]
        assert login(world.b.operator).get(f"/api/alerts?plate={a_plate}").json() == []
        found = login(world.a.operator).get(f"/api/alerts?plate={a_plate}").json()
        assert len(found) == 1 and found[0]["plate_masked"].startswith(a_plate[0])

    def test_tenant_comes_from_token_not_from_request(self, world: World, login: Any) -> None:
        b = login(world.b.operator)
        # Client-supplied tenant hints are ignored entirely.
        r = b.get(
            "/api/alerts",
            params={"tenant_id": str(world.a.id)},
            headers={"X-Tenant-ID": str(world.a.id)},
        )
        assert {x["id"] for x in r.json()}.isdisjoint({str(x) for x in world.data["a"]["alerts"]})
        assert b.get("/api/tenants/current").json()["id"] == str(world.b.id)

    def test_cannot_create_alert_on_foreign_camera(self, world: World, login: Any) -> None:
        b = login(world.b.operator)
        r = b.post(
            "/api/alerts",
            {
                "camera_id": str(world.data["a"]["camera"]),
                "priority": "high",
                "event_type": "test",
                "description": "spoof",
            },
        )
        assert r.status_code == 404

    def test_patrol_sees_only_assigned_alerts(self, world: World, login: Any) -> None:
        patrol = login(world.a.patrol)
        listed = [x["id"] for x in patrol.get("/api/alerts").json()]
        assert listed == [str(world.data["a"]["assigned_alert"])]
        unassigned = world.data["a"]["alerts"][0]
        assert patrol.get(f"/api/alerts/{unassigned}").status_code == 404
        assert patrol.get(f"/api/alerts/{world.data['a']['assigned_alert']}").status_code == 200


class TestDatabaseIsolation:
    def _count(self, conn: psycopg.Connection[Any], table: str) -> int:
        row = conn.execute(f"SELECT count(*) FROM {table}").fetchone()
        assert row is not None
        return int(row[0])

    def test_missing_tenant_setting_returns_zero_rows(self, world: World) -> None:
        with app_conn() as conn:
            for table in ("tenants", *TENANT_SCOPED_TABLES):
                assert self._count(conn, table) == 0, table

    def test_wrong_tenant_setting_returns_only_that_tenant(self, world: World) -> None:
        with app_conn() as conn:
            conn.execute("SELECT set_config('app.tenant_id', %s, false)", (str(world.b.id),))
            rows = conn.execute(
                "SELECT count(*) FROM alerts WHERE id = ANY(%s)", (world.data["a"]["alerts"],)
            ).fetchone()
            assert rows == (0,)
            assert conn.execute(
                "SELECT count(*) FROM alerts WHERE tenant_id = %s", (world.a.id,)
            ).fetchone() == (0,)
            conn.execute("SELECT set_config('app.tenant_id', %s, false)", (str(uuid.uuid4()),))
            for table in ("tenants", *TENANT_SCOPED_TABLES):
                assert self._count(conn, table) == 0, table

    def test_set_local_does_not_leak_across_transactions(self, world: World) -> None:
        with app_conn() as conn:
            with conn.transaction():
                conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(world.a.id),))
                assert self._count(conn, "alerts") == 3
            assert self._count(conn, "alerts") == 0

    def test_insert_or_update_into_other_tenant_rejected(self, world: World) -> None:
        with app_conn() as conn:
            conn.execute("SELECT set_config('app.tenant_id', %s, false)", (str(world.b.id),))
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(
                    "INSERT INTO cameras (id, tenant_id, name, location, is_active, created_at) "
                    "VALUES (gen_random_uuid(), %s, 'x', 'y', true, now())",
                    (world.a.id,),
                )
            conn.rollback()
            conn.execute("SELECT set_config('app.tenant_id', %s, false)", (str(world.b.id),))
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute("UPDATE cameras SET tenant_id = %s", (world.a.id,))
            conn.rollback()
            conn.execute("SELECT set_config('app.tenant_id', %s, false)", (str(world.b.id),))
            result = conn.execute(
                "DELETE FROM alerts WHERE id = ANY(%s)", (world.data["a"]["alerts"],)
            )
            assert result.rowcount == 0

    def test_cross_tenant_foreign_key_rejected(self, world: World) -> None:
        with app_conn() as conn:
            conn.execute("SELECT set_config('app.tenant_id', %s, false)", (str(world.b.id),))
            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                conn.execute(
                    "INSERT INTO alerts (id, tenant_id, camera_id, priority, status, event_type, "
                    "description, detected_at, created_at) VALUES (gen_random_uuid(), %s, %s, "
                    "'high', 'new', 't', 'd', now(), now())",
                    (world.b.id, world.data["a"]["camera"]),
                )

    def test_app_role_attributes(self) -> None:
        with app_conn() as conn:
            row = conn.execute(
                "SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb FROM pg_roles "
                "WHERE rolname = current_user"
            ).fetchone()
            assert row == (False, False, False, False)
            owned = conn.execute(
                "SELECT count(*) FROM pg_tables "
                "WHERE schemaname = 'public' AND tableowner = current_user"
            ).fetchone()
            assert owned == (0,)
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute("ALTER TABLE alerts DISABLE ROW LEVEL SECURITY")

    def test_rls_enabled_and_forced_on_every_tenant_table(self) -> None:
        with admin_conn() as conn:
            rows = dict(
                (r[0], (r[1], r[2]))
                for r in conn.execute(
                    "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
                    "WHERE relname = ANY(%s)",
                    (["tenants", *TENANT_SCOPED_TABLES],),
                ).fetchall()
            )
        assert set(rows) == {"tenants", *TENANT_SCOPED_TABLES}
        assert all(v == (True, True) for v in rows.values()), rows

    def test_every_table_with_tenant_id_is_protected(self) -> None:
        """Guards against a future migration adding a tenant table without a policy."""
        with admin_conn() as conn:
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT table_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND column_name = 'tenant_id'"
                ).fetchall()
            }
            policies = {
                r[0]
                for r in conn.execute("SELECT tablename FROM pg_policies WHERE schemaname='public'")
            }
        assert tables <= policies and tables == set(TENANT_SCOPED_TABLES)


class TestRbac:
    @pytest.mark.parametrize(
        ("role", "method", "path", "expected"),
        [
            ("auditor", "get", "/api/alerts", 403),
            ("auditor", "get", "/api/audit/verify", 200),
            ("patrol", "get", "/api/audit/chain", 403),
            ("operator", "get", "/api/audit/chain", 403),
            ("operator", "get", "/api/users", 403),
            ("patrol", "post", "/api/alerts/{alert}/confirm", 403),
            ("operator", "post", "/api/alerts/{alert}/confirm", 200),
            ("auditor", "get", "/api/cameras", 403),
            ("operator", "post", "/api/tenants", 403),
            ("tenant_admin", "post", "/api/tenants", 403),
        ],
    )
    def test_matrix(
        self, world: World, login: Any, role: str, method: str, path: str, expected: int
    ) -> None:
        from app.models import Role

        c: ApiClient = login(world.a.users[Role(role)])
        url = path.format(alert=world.data["a"]["alerts"][0])
        body = (
            {"name": "x", "slug": "xx", "admin_email": "q@test.local"}
            if "tenants" in path
            else None
        )
        r = getattr(c, method)(url, **({"json": body} if body else {}))
        assert r.status_code == expected, (role, path, r.text)

    def test_denials_are_audited(self, world: World, login: Any) -> None:
        login(world.a.auditor).get("/api/alerts")
        assert "security.access_denied" in audit_actions(world.a.id)


class TestMigrationIntegrity:
    def test_models_match_migrations_and_protected_constraints_survive(self) -> None:
        """Fails when a model change is not migrated, and when autogenerate would drop the
        composite tenant FKs (they must stay protected by alembic/env.py)."""
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext
        from sqlalchemy import create_engine

        from app.migration_filters import include_object
        from app.models import Base
        from tests.conftest import MIGRATOR_URL

        engine = create_engine(MIGRATOR_URL)
        try:
            with engine.connect() as conn:
                ctx = MigrationContext.configure(conn, opts={"include_object": include_object})
                diff = compare_metadata(ctx, Base.metadata)
        finally:
            engine.dispose()
        assert diff == [], diff

        with admin_conn() as conn:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT conname FROM pg_constraint WHERE conname LIKE 'fk_%%_tenant_%%'"
                ).fetchall()
            }
        assert {
            "fk_alerts_tenant_camera",
            "fk_evidence_tenant_alert",
            "fk_service_keys_tenant_account",
        } <= names
