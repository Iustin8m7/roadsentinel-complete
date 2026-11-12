"""Tamper-evident audit log: hash chain integrity, tamper detection and DB-level append-only."""

from __future__ import annotations

import uuid
from typing import Any

import psycopg
import pytest

from app.core import audit
from app.core.audit import AuditAction, verify_chain
from app.db import tenant_session
from tests.conftest import World, admin_conn, app_conn, audit_actions


def _fill(tenant_id: uuid.UUID, n: int = 50) -> None:
    for i in range(n):
        audit.record(
            tenant_id,
            AuditAction.alert_confirmed,
            actor_id=uuid.uuid4(),
            resource_type="alerts",
            resource_id=uuid.uuid4(),
            details={"i": i, "note": f"entry {i}", "nested": {"ok": True}},
        )


def _verify(tenant_id: uuid.UUID) -> audit.VerifyResult:
    with tenant_session(tenant_id) as db:
        return verify_chain(db, tenant_id)


def _tamper(sql: str, *params: Any) -> None:
    """Privileged attacker: superuser connection with triggers disabled."""
    with admin_conn() as conn:
        conn.execute("SET session_replication_role = replica")
        conn.execute(sql, params)


class TestChain:
    def test_verifies_after_many_inserts(self, world: World) -> None:
        _fill(world.a.id, 120)
        result = _verify(world.a.id)
        assert result.ok and result.checked >= 120 and result.head_hash

    def test_chains_are_per_tenant(self, world: World) -> None:
        _fill(world.a.id, 5)
        _fill(world.b.id, 3)
        with admin_conn() as conn:
            rows = conn.execute(
                "SELECT tenant_id, min(seq), max(seq), count(*) FROM audit_log GROUP BY tenant_id"
            ).fetchall()
        for _tid, lo, hi, cnt in rows:
            assert lo == 1 and hi == cnt
        assert _verify(world.a.id).ok and _verify(world.b.id).ok

    def test_secrets_are_redacted_in_details(self, world: World) -> None:
        audit.record(
            world.a.id, "test.event", details={"password": "hunter2-hunter2", "token": "abc"}
        )
        with admin_conn() as conn:
            row = conn.execute(
                "SELECT details::text FROM audit_log WHERE action = 'test.event'"
            ).fetchone()
        assert row and "hunter2" not in row[0] and "abc" not in row[0]

    @pytest.mark.parametrize(
        ("column", "value"),
        [
            ("action", "'auth.login.success'"),
            ("actor_id", "gen_random_uuid()"),
            ("resource_id", "'forged'"),
            ("ip", "'10.6.6.6'"),
            ("user_agent", "'curl'"),
            ("details", "'{\"i\": 999}'::jsonb"),
            ("ts", "ts + interval '1 hour'"),
            ("prev_hash", "repeat('a', 64)"),
            ("entry_hash", "repeat('b', 64)"),
            ("resource_type", "'users'"),
        ],
    )
    def test_any_field_modification_detected(self, world: World, column: str, value: str) -> None:
        _fill(world.a.id, 10)
        _tamper(
            f"UPDATE audit_log SET {column} = {value} WHERE tenant_id = %s AND seq = 5",
            world.a.id,
        )
        result = _verify(world.a.id)
        assert not result.ok
        assert result.first_broken_seq in (5, 6)

    def test_deleted_row_detected(self, world: World) -> None:
        _fill(world.a.id, 10)
        _tamper("DELETE FROM audit_log WHERE tenant_id = %s AND seq = 4", world.a.id)
        result = _verify(world.a.id)
        assert not result.ok and result.first_broken_seq == 5

    def test_reordered_rows_detected(self, world: World) -> None:
        _fill(world.a.id, 10)
        for src, dst in ((3, -1), (7, 3), (-1, 7)):  # swap entries 3 and 7
            _tamper(
                "UPDATE audit_log SET seq = %s WHERE tenant_id = %s AND seq = %s",
                dst,
                world.a.id,
                src,
            )
        result = _verify(world.a.id)
        assert not result.ok and result.first_broken_seq == 3

    def test_recomputed_entry_is_still_detected_downstream(self, world: World) -> None:
        """An attacker who rewrites one entry *and* fixes its hash still breaks the next link."""
        _fill(world.a.id, 10)
        with tenant_session(world.a.id) as db:
            from app.models import AuditLog

            entry = db.query(AuditLog).filter_by(tenant_id=world.a.id, seq=4).one()
            entry.details = {"i": 12345}
            forged = audit.compute_hash(entry)
            db.rollback()
        _tamper(
            "UPDATE audit_log SET details = '{\"i\": 12345}'::jsonb, entry_hash = %s "
            "WHERE tenant_id = %s AND seq = 4",
            forged,
            world.a.id,
        )
        result = _verify(world.a.id)
        assert (
            not result.ok and result.first_broken_seq == 5 and result.reason == "prev_hash mismatch"
        )


class TestAppendOnly:
    def _ctx(self, conn: psycopg.Connection[Any], tenant_id: uuid.UUID) -> None:
        conn.execute("SELECT set_config('app.tenant_id', %s, false)", (str(tenant_id),))

    @pytest.mark.parametrize(
        "sql",
        [
            "UPDATE audit_log SET action = 'x'",
            "DELETE FROM audit_log",
            "TRUNCATE audit_log",
        ],
    )
    def test_app_role_cannot_modify(self, world: World, sql: str) -> None:
        _fill(world.a.id, 3)
        with app_conn() as conn:
            self._ctx(conn, world.a.id)
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(sql)

    def test_trigger_blocks_even_the_table_owner(self, world: World) -> None:
        _fill(world.a.id, 3)
        from tests.conftest import MIGRATOR_URL, _plain

        with psycopg.connect(_plain(MIGRATOR_URL)) as conn:
            for sql in (
                "UPDATE audit_log SET action = 'x'",
                "DELETE FROM audit_log",
                "TRUNCATE audit_log",
            ):
                with pytest.raises(psycopg.errors.InsufficientPrivilege, match="append-only"):
                    conn.execute(sql)
                conn.rollback()

    def test_superuser_without_disabling_triggers_is_blocked(self, world: World) -> None:
        _fill(world.a.id, 3)
        with admin_conn() as conn, pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("DELETE FROM audit_log")


class TestEndpoints:
    def test_verify_endpoint_ok_then_broken(self, world: World, login: Any) -> None:
        _fill(world.a.id, 20)
        auditor = login(world.a.auditor)
        r = auditor.get("/api/audit/verify")
        assert r.status_code == 200 and r.json()["ok"] is True
        _tamper("UPDATE audit_log SET ip = '6.6.6.6' WHERE tenant_id = %s AND seq = 7", world.a.id)
        body = auditor.get("/api/audit/verify").json()
        assert body["ok"] is False and body["first_broken_seq"] == 7
        assert audit_actions(world.a.id).count("audit.verified") == 2

    def test_listing_requires_audit_role(self, world: World, login: Any) -> None:
        assert login(world.a.operator).get("/api/audit/chain").status_code == 403
        entries = login(world.a.auditor).get("/api/audit/chain?limit=5").json()
        assert 0 < len(entries) <= 5 and entries[0]["seq"] > entries[-1]["seq"]

    def test_key_actions_are_logged(self, world: World, login: Any) -> None:
        op = login(world.a.operator)
        op.post(f"/api/alerts/{world.data['a']['alerts'][0]}/confirm")
        op.post(f"/api/alerts/{world.data['a']['alerts'][2]}/reject")
        op.post(f"/api/evidence/{world.data['a']['evidence']}/access", {"variant": "redacted"})
        actions = audit_actions(world.a.id)
        for expected in (
            "alert.confirmed",
            "alert.rejected",
            "evidence.url_issued",
            "auth.login.success",
        ):
            assert expected in actions
