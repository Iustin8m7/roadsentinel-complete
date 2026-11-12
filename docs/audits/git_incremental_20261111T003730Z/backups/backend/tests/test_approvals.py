"""Four-eyes rule: unblur and export requests need a different tenant admin's approval and
produce a time-limited, revocable, audited grant for the requester only."""

from __future__ import annotations

import uuid
from typing import Any

from app.models import Role
from tests.conftest import ApiClient, World, admin_conn, audit_actions, make_user

JUSTIFICATION = "Plate needed to identify the vehicle for case report"


def _request(c: ApiClient, evidence_id: uuid.UUID, kind: str = "unblur") -> dict[str, Any]:
    r = c.post(
        "/api/approvals",
        {
            "kind": kind,
            "evidence_id": str(evidence_id),
            "justification": JUSTIFICATION,
            "case_reference": "CASE-2026-0042",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _original_url(c: ApiClient, evidence_id: uuid.UUID) -> Any:
    return c.post(f"/api/evidence/{evidence_id}/access", {"variant": "original"})


class TestUnblur:
    def test_full_flow_and_audit(self, world: World, login: Any) -> None:
        ev = world.data["a"]["evidence"]
        op, admin = login(world.a.operator), login(world.a.admin)
        assert _original_url(op, ev).status_code == 403  # blurred by default
        assert op.get(f"/api/evidence/{ev}").json()["plate"] is None

        req = _request(op, ev)
        assert req["status"] == "pending" and req["grant_active"] is False
        assert _original_url(op, ev).status_code == 403  # pending is not a grant

        approved = admin.post(f"/api/approvals/{req['id']}/approve", {"note": "ok"}).json()
        assert approved["status"] == "approved" and approved["grant_active"] is True

        r = _original_url(op, ev)
        assert r.status_code == 200
        content = op.get(r.json()["url"])
        assert content.status_code == 200 and content.content.startswith(b"\x89PNG")
        assert op.get(f"/api/evidence/{ev}").json()["plate"] == world.data["a"]["plates"][1]

        # The grant belongs to the requester only, not to the approver or colleagues.
        assert _original_url(admin, ev).status_code == 403
        assert _original_url(login(world.a.admin), ev).status_code == 403

        actions = audit_actions(world.a.id)
        for expected in (
            "approval.requested",
            "approval.approved",
            "evidence.url_issued",
            "evidence.viewed",
        ):
            assert expected in actions, expected
        # Every view during the grant is audited.
        op.get(_original_url(op, ev).json()["url"])
        assert audit_actions(world.a.id).count("evidence.viewed") >= 3

    def test_justification_and_case_reference_required(self, world: World, login: Any) -> None:
        op = login(world.a.operator)
        ev = str(world.data["a"]["evidence"])
        assert (
            op.post(
                "/api/approvals",
                {"evidence_id": ev, "justification": "short", "case_reference": "C-1"},
            ).status_code
            == 422
        )
        assert (
            op.post(
                "/api/approvals", {"evidence_id": ev, "justification": JUSTIFICATION}
            ).status_code
            == 422
        )

    def test_self_approval_rejected_server_side(self, world: World, login: Any) -> None:
        admin = login(world.a.admin)  # admins may request too
        req = _request(admin, world.data["a"]["evidence"])
        r = admin.post(f"/api/approvals/{req['id']}/approve")
        assert r.status_code == 403
        assert admin.post(f"/api/approvals/{req['id']}/deny").status_code == 403
        assert "approval.self_approval_blocked" in audit_actions(world.a.id)
        with admin_conn() as conn:
            assert conn.execute("SELECT status FROM approval_requests").fetchone() == ("pending",)

    def test_second_admin_can_approve_admin_request(self, world: World, login: Any) -> None:
        admin2 = make_user(world.a.id, Role.tenant_admin, "admin2.a@test.local")
        req = _request(login(world.a.admin), world.data["a"]["evidence"])
        assert login(admin2).post(f"/api/approvals/{req['id']}/approve").status_code == 200

    def test_non_admin_cannot_approve(self, world: World, login: Any) -> None:
        req = _request(login(world.a.operator), world.data["a"]["evidence"])
        other_op = make_user(world.a.id, Role.operator, "op2.a@test.local")
        for user in (other_op, world.a.patrol, world.a.auditor):
            assert login(user).post(f"/api/approvals/{req['id']}/approve").status_code == 403

    def test_cross_tenant_approval_rejected(self, world: World, login: Any) -> None:
        req = _request(login(world.a.operator), world.data["a"]["evidence"])
        b_admin = login(world.b.admin)
        assert b_admin.post(f"/api/approvals/{req['id']}/approve").status_code == 404
        assert b_admin.get(f"/api/approvals/{req['id']}").status_code == 404
        assert "security.cross_tenant_access" in audit_actions(world.a.id)
        with admin_conn() as conn:
            assert conn.execute("SELECT status FROM approval_requests").fetchone() == ("pending",)

    def test_expired_grant_rejected(self, world: World, login: Any) -> None:
        ev = world.data["a"]["evidence"]
        op = login(world.a.operator)
        req = _request(op, ev)
        login(world.a.admin).post(f"/api/approvals/{req['id']}/approve")
        url = _original_url(op, ev).json()["url"]  # issued while the grant was valid
        with admin_conn() as conn:
            conn.execute(
                "UPDATE approval_requests SET grant_expires_at = now() - interval '1 second'"
            )
        assert _original_url(op, ev).status_code == 403
        assert op.get(url).status_code == 403  # re-checked at view time
        assert op.get(f"/api/approvals/{req['id']}").json()["grant_active"] is False

    def test_grant_lasts_30_minutes(self, world: World, login: Any) -> None:
        req = _request(login(world.a.operator), world.data["a"]["evidence"])
        login(world.a.admin).post(f"/api/approvals/{req['id']}/approve")
        with admin_conn() as conn:
            delta = conn.execute(
                "SELECT grant_expires_at - decided_at FROM approval_requests"
            ).fetchone()[0]
        assert delta.total_seconds() == 30 * 60

    def test_revoked_grant_rejected(self, world: World, login: Any) -> None:
        ev = world.data["a"]["evidence"]
        op, admin = login(world.a.operator), login(world.a.admin)
        req = _request(op, ev)
        admin.post(f"/api/approvals/{req['id']}/approve")
        url = _original_url(op, ev).json()["url"]
        assert admin.post(f"/api/approvals/{req['id']}/revoke").status_code == 200
        assert op.get(url).status_code == 403
        assert _original_url(op, ev).status_code == 403
        assert "approval.revoked" in audit_actions(world.a.id)

    def test_approval_requires_fresh_mfa(self, world: World, login: Any) -> None:
        req = _request(login(world.a.operator), world.data["a"]["evidence"])
        admin = login(world.a.admin)
        with admin_conn() as conn:
            conn.execute(
                "UPDATE user_sessions SET mfa_verified_at = now() - interval '6 minutes' "
                "WHERE user_id = %s",
                (world.a.admin.id,),
            )
        r = admin.post(f"/api/approvals/{req['id']}/approve")
        assert r.status_code == 403 and r.json()["detail"] == "reauth_required"

    def test_denied_request_grants_nothing(self, world: World, login: Any) -> None:
        ev = world.data["a"]["evidence"]
        op = login(world.a.operator)
        req = _request(op, ev)
        assert (
            login(world.a.admin).post(f"/api/approvals/{req['id']}/deny").json()["status"]
            == "denied"
        )
        assert _original_url(op, ev).status_code == 403
        assert "approval.denied" in audit_actions(world.a.id)

    def test_requester_sees_only_own_requests(self, world: World, login: Any) -> None:
        _request(login(world.a.operator), world.data["a"]["evidence"])
        other = make_user(world.a.id, Role.operator, "op3.a@test.local")
        assert login(other).get("/api/approvals").json() == []
        assert len(login(world.a.admin).get("/api/approvals").json()) == 1


class TestExport:
    def test_export_needs_its_own_approval_and_fresh_mfa(self, world: World, login: Any) -> None:
        ev = world.data["a"]["evidence"]
        op, admin = login(world.a.operator), login(world.a.admin)
        assert op.post(f"/api/evidence/{ev}/export").status_code == 403
        # An unblur grant does not authorize export.
        unblur = _request(op, ev, "unblur")
        admin.post(f"/api/approvals/{unblur['id']}/approve")
        assert op.post(f"/api/evidence/{ev}/export").status_code == 403

        exp = _request(op, ev, "export")
        assert op.post(f"/api/approvals/{exp['id']}/approve").status_code == 403  # operator can't
        admin.post(f"/api/approvals/{exp['id']}/approve")
        r = op.post(f"/api/evidence/{ev}/export")
        assert r.status_code == 200
        dl = op.get(r.json()["url"])
        assert dl.status_code == 200 and dl.headers["content-disposition"].startswith("attachment")
        assert "evidence.exported" in audit_actions(world.a.id)

        with admin_conn() as conn:
            conn.execute(
                "UPDATE user_sessions SET mfa_verified_at = now() - interval '6 minutes' "
                "WHERE user_id = %s",
                (world.a.operator.id,),
            )
        assert op.post(f"/api/evidence/{ev}/export").json()["detail"] == "reauth_required"
