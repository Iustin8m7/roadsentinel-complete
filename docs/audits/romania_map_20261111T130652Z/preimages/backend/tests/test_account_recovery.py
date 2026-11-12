"""Four-eyes account recovery, own password change, session revocation, break-glass CLI."""

from __future__ import annotations

from typing import Any

from app.models import Role
from tests.conftest import ApiClient, World, admin_conn, audit_actions, make_user

WHY = "Operator lost the phone with the authenticator; identity checked in person"
NEW_PW = "Brand-New-Horse-Staple-77"


def request_reset(admin: ApiClient, target: Any, *, reset_mfa: bool = False) -> Any:
    return admin.post(
        f"/api/users/{target.id}/reset-requests",
        {"reset_mfa": reset_mfa, "justification": WHY, "case_reference": "CASE-77"},
    )


def full_flow(world: World, login: Any, target: Any, reset_mfa: bool = False) -> str:
    """admin A requests, admin B approves, A issues; returns the token."""
    a = login(world.a.admin)
    second = make_user(world.a.id, Role.tenant_admin, "second.admin@test.local")
    b = login(second)
    r = request_reset(a, target, reset_mfa=reset_mfa)
    assert r.status_code == 201, r.text
    approval = r.json()
    assert approval["kind"] == "account_reset" and approval["status"] == "pending"
    assert b.post(f"/api/approvals/{approval['id']}/approve", {"note": "ok"}).status_code == 200
    issued = a.post(f"/api/users/reset-requests/{approval['id']}/issue")
    assert issued.status_code == 200, issued.text
    return issued.json()["token"]


class TestRequestAndApproval:
    def test_complete_flow_resets_the_password_and_keeps_mfa(
        self, world: World, login: Any
    ) -> None:
        op = world.a.operator
        old_session = login(op)
        assert old_session.get("/api/auth/me").status_code == 200
        token = full_flow(world, login, op)

        c = ApiClient()
        info = c.post("/api/auth/reset/inspect", {"token": token})
        assert (
            info.status_code == 200
            and info.json()["email"] == op.email
            and info.json()["reset_mfa"] is False
        )
        assert (
            c.post("/api/auth/reset/accept", {"token": token, "password": NEW_PW}).status_code
            == 204
        )

        assert old_session.get("/api/auth/me").status_code == 401  # every session was revoked
        fresh = ApiClient()
        assert (
            fresh.post("/api/auth/login", {"email": op.email, "password": op.password}).status_code
            == 401
        )
        r = fresh.post("/api/auth/login", {"email": op.email, "password": NEW_PW})
        assert (
            r.status_code == 200
            and r.json()["mfa_required"] is True
            and r.json()["enrollment_required"] is False
        )
        assert (
            fresh.post("/api/auth/mfa/verify", {"code": op.totp()}).status_code == 204
        )  # same authenticator
        acts = audit_actions(world.a.id)
        for a in (
            "user.reset.requested",
            "approval.approved",
            "user.reset.issued",
            "user.reset.completed",
        ):
            assert a in acts

    def test_reset_mfa_forces_a_new_enrollment(self, world: World, login: Any) -> None:
        op = world.a.operator
        token = full_flow(world, login, op, reset_mfa=True)
        assert (
            ApiClient()
            .post("/api/auth/reset/accept", {"token": token, "password": NEW_PW})
            .status_code
            == 204
        )
        fresh = ApiClient()
        r = fresh.post("/api/auth/login", {"email": op.email, "password": NEW_PW})
        assert r.json() == {"mfa_required": True, "enrollment_required": True}
        with admin_conn() as conn:
            row = conn.execute(
                "SELECT mfa_enabled, totp_secret_enc IS NULL FROM users WHERE id = %s", (op.id,)
            ).fetchone()
            codes = conn.execute(
                "SELECT count(*) FROM recovery_codes WHERE user_id = %s", (op.id,)
            ).fetchone()[0]
        assert row == (False, True) and codes == 0

    def test_nobody_approves_their_own_request(self, world: World, login: Any) -> None:
        a = login(world.a.admin)
        r = request_reset(a, world.a.operator).json()
        assert a.post(f"/api/approvals/{r['id']}/approve", {}).status_code == 403
        assert "approval.self_approval_blocked" in audit_actions(world.a.id)

    def test_token_cannot_be_issued_before_approval_or_by_someone_else_or_twice(
        self, world: World, login: Any
    ) -> None:
        a = login(world.a.admin)
        b = login(make_user(world.a.id, Role.tenant_admin, "second.admin@test.local"))
        req = request_reset(a, world.a.operator).json()
        assert (
            a.post(f"/api/users/reset-requests/{req['id']}/issue").status_code == 403
        )  # not approved yet
        b.post(f"/api/approvals/{req['id']}/approve", {})
        assert (
            b.post(f"/api/users/reset-requests/{req['id']}/issue").status_code == 404
        )  # approver is not the requester
        assert a.post(f"/api/users/reset-requests/{req['id']}/issue").status_code == 200
        assert a.post(f"/api/users/reset-requests/{req['id']}/issue").status_code == 409  # consumed

    def test_denied_request_never_yields_a_token(self, world: World, login: Any) -> None:
        a = login(world.a.admin)
        b = login(make_user(world.a.id, Role.tenant_admin, "second.admin@test.local"))
        req = request_reset(a, world.a.operator).json()
        assert b.post(f"/api/approvals/{req['id']}/deny", {"note": "no"}).status_code == 200
        assert a.post(f"/api/users/reset-requests/{req['id']}/issue").status_code == 403

    def test_rules_about_who_can_be_reset(self, world: World, login: Any) -> None:
        a = login(world.a.admin)
        assert request_reset(a, world.a.admin).status_code == 400  # not yourself
        first = request_reset(a, world.a.operator)
        assert first.status_code == 201
        assert request_reset(a, world.a.operator).status_code == 409  # already pending
        assert (
            login(world.a.operator)
            .post(
                f"/api/users/{world.a.patrol.id}/reset-requests",
                {"justification": WHY, "case_reference": "CASE-1"},
            )
            .status_code
            == 403
        )  # operators cannot
        assert (
            request_reset(a, world.b.operator).status_code == 404
        )  # other tenant: invisible (RLS)
        assert (
            a.post(
                f"/api/users/{world.a.operator.id}/reset-requests",
                {"justification": "short", "case_reference": "C"},
            ).status_code
            == 422
        )

    def test_the_generic_approvals_endpoint_cannot_create_reset_requests(
        self, world: World, login: Any
    ) -> None:
        a = login(world.a.admin)
        r = a.post(
            "/api/approvals",
            {
                "kind": "account_reset",
                "evidence_id": str(world.data["a"]["evidence"]),
                "justification": WHY,
                "case_reference": "CASE-1",
            },
        )
        assert r.status_code == 422


class TestTokenSecurity:
    def test_token_is_single_use_and_garbage_is_rejected(self, world: World, login: Any) -> None:
        token = full_flow(world, login, world.a.operator)
        c = ApiClient()
        assert (
            c.post("/api/auth/reset/accept", {"token": token, "password": NEW_PW}).status_code
            == 204
        )
        assert (
            c.post("/api/auth/reset/accept", {"token": token, "password": NEW_PW + "x"}).status_code
            == 401
        )
        assert c.post("/api/auth/reset/inspect", {"token": "x" * 40}).status_code == 401

    def test_weak_password_does_not_consume_the_token(self, world: World, login: Any) -> None:
        token = full_flow(world, login, world.a.operator)
        c = ApiClient()
        assert (
            c.post(
                "/api/auth/reset/accept", {"token": token, "password": "password1234"}
            ).status_code
            == 422
        )
        assert (
            c.post("/api/auth/reset/accept", {"token": token, "password": NEW_PW}).status_code
            == 204
        )

    def test_an_invitation_token_is_not_a_reset_token_and_vice_versa(
        self, world: World, login: Any
    ) -> None:
        a = login(world.a.admin)
        inv = a.post(
            "/api/users/invitations", {"email": "new.person@test.local", "role": "operator"}
        ).json()["token"]
        c = ApiClient()
        assert c.post("/api/auth/reset/inspect", {"token": inv}).status_code == 401
        reset = full_flow(world, login, world.a.patrol)
        assert c.post("/api/auth/invitations/inspect", {"token": reset}).status_code == 401

    def test_expired_token_is_refused(self, world: World, login: Any) -> None:
        token = full_flow(world, login, world.a.operator)
        with admin_conn() as conn:
            conn.execute(
                "UPDATE invitations SET expires_at = now() - interval '1 minute' "
                "WHERE kind = 'reset'"
            )
            conn.commit()
        assert ApiClient().post("/api/auth/reset/inspect", {"token": token}).status_code == 401

    def test_disabled_account_cannot_be_recovered(self, world: World, login: Any) -> None:
        token = full_flow(world, login, world.a.operator)
        with admin_conn() as conn:
            conn.execute("UPDATE users SET is_active = false WHERE id = %s", (world.a.operator.id,))
            conn.commit()
        assert (
            ApiClient()
            .post("/api/auth/reset/accept", {"token": token, "password": NEW_PW})
            .status_code
            == 401
        )


class TestOwnPasswordAndSessions:
    def test_change_password_needs_current_password_and_revokes_other_sessions(
        self, world: World, login: Any
    ) -> None:
        op = world.a.operator
        here, other = login(op), login(op)
        assert (
            here.post(
                "/api/auth/password",
                {"current_password": "wrong-password-1", "new_password": NEW_PW},
            ).status_code
            == 401
        )
        assert (
            here.post(
                "/api/auth/password", {"current_password": op.password, "new_password": "short"}
            ).status_code
            == 422
        )
        assert (
            here.post(
                "/api/auth/password", {"current_password": op.password, "new_password": op.password}
            ).status_code
            == 422
        )
        assert (
            here.post(
                "/api/auth/password", {"current_password": op.password, "new_password": NEW_PW}
            ).status_code
            == 204
        )
        assert here.get("/api/auth/me").status_code == 200  # this session survives
        assert other.get("/api/auth/me").status_code == 401  # the other device is signed out
        assert (
            ApiClient().post("/api/auth/login", {"email": op.email, "password": NEW_PW}).status_code
            == 200
        )
        assert "user.password.changed" in audit_actions(world.a.id)

    def test_revoke_other_sessions(self, world: World, login: Any) -> None:
        op = world.a.operator
        here, d2, d3 = login(op), login(op), login(op)
        r = here.post("/api/sessions/revoke-others")
        assert r.status_code == 200 and r.json() == {"revoked": 2}
        assert here.get("/api/auth/me").status_code == 200
        assert (
            d2.get("/api/auth/me").status_code == 401 and d3.get("/api/auth/me").status_code == 401
        )

    def test_admin_can_sign_a_user_out_everywhere_but_operators_cannot(
        self, world: World, login: Any
    ) -> None:
        victim = login(world.a.operator)
        assert (
            login(world.a.operator)
            .post(f"/api/users/{world.a.patrol.id}/sessions/revoke-all")
            .status_code
            == 403
        )
        r = login(world.a.admin).post(f"/api/users/{world.a.operator.id}/sessions/revoke-all")
        assert r.status_code == 200 and r.json()["revoked"] >= 2
        assert victim.get("/api/auth/me").status_code == 401


def test_break_glass_cli_issues_a_working_audited_token(world: World, capsys: Any) -> None:
    from app.cli import main

    op = world.a.operator
    main(["reset-account", "--tenant", "unit-a", "--email", op.email, "--reset-mfa"])
    token = capsys.readouterr().out.split("shown once, valid 60 min): ")[1].splitlines()[0].strip()
    c = ApiClient()
    assert c.post("/api/auth/reset/accept", {"token": token, "password": NEW_PW}).status_code == 204
    assert (
        c.post("/api/auth/login", {"email": op.email, "password": NEW_PW}).json()[
            "enrollment_required"
        ]
        is True
    )
    assert "user.reset.issued" in audit_actions(world.a.id)
