"""Authentication: password + mandatory MFA, enrollment, lockout, rate limits, sessions,
refresh rotation and reuse detection, CSRF, cookies, re-authentication, invitations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pyotp
import pytest

from app.core.http import ACCESS, MFA, REFRESH, cookie_name
from app.models import Role
from tests.conftest import (
    ORIGIN,
    PASSWORD,
    ApiClient,
    World,
    admin_conn,
    audit_actions,
    make_user,
    reset_totp_step,
)


def _password_step(c: ApiClient, email: str, password: str = PASSWORD) -> object:
    return c.post("/api/auth/login", {"email": email, "password": password})


class TestLogin:
    def test_full_login_with_mfa(self, world: World, client: ApiClient) -> None:
        user = world.a.operator
        r = _password_step(client, user.email)
        assert r.status_code == 200 and r.json() == {
            "mfa_required": True,
            "enrollment_required": False,
        }
        # Password alone grants nothing.
        assert client.get("/api/auth/me").status_code == 401
        assert client.get("/api/alerts").status_code == 401
        r = client.post("/api/auth/mfa/verify", {"code": user.totp()})
        assert r.status_code == 204
        me = client.get("/api/auth/me").json()
        assert me["email"] == user.email and me["role"] == "operator"
        assert "login_success" not in audit_actions(world.a.id)  # sanity: actions use dotted names
        assert "auth.login.success" in audit_actions(world.a.id)
        assert "auth.mfa.success" in audit_actions(world.a.id)

    def test_cookie_flags(self, world: World, client: ApiClient) -> None:
        _password_step(client, world.a.operator.email)
        r = client.post("/api/auth/mfa/verify", {"code": world.a.operator.totp()})
        cookies = r.headers.get_list("set-cookie")
        access = next(c for c in cookies if c.startswith(cookie_name(ACCESS) + "="))
        refresh = next(c for c in cookies if c.startswith(cookie_name(REFRESH) + "="))
        for c in (access, refresh):
            lowered = c.lower()
            assert "httponly" in lowered and "secure" in lowered and "samesite=strict" in lowered
        assert "Path=/api;" in access or access.endswith("Path=/api")
        assert "Path=/api/auth" in refresh
        assert cookie_name(ACCESS).startswith("__Secure-")

    def test_unknown_account_and_wrong_password_are_indistinguishable(
        self, world: World, client: ApiClient
    ) -> None:
        r1 = _password_step(client, "nobody@test.local")
        r2 = _password_step(client, world.a.operator.email, "Wrong-password-123")
        assert r1.status_code == r2.status_code == 401
        assert r1.json() == r2.json() == {"detail": "Invalid credentials"}
        assert "auth.login.failure" in audit_actions(world.platform.id)  # unknown account
        assert "auth.login.failure" in audit_actions(world.a.id)

    def test_wrong_totp_rejected(self, world: World, client: ApiClient) -> None:
        _password_step(client, world.a.operator.email)
        r = client.post("/api/auth/mfa/verify", {"code": "000000"})
        assert r.status_code == 401
        assert client.get("/api/auth/me").status_code == 401
        assert "auth.mfa.failure" in audit_actions(world.a.id)

    def test_totp_code_cannot_be_replayed(self, world: World) -> None:
        user = world.a.operator
        code = user.totp()
        c1 = ApiClient()
        _password_step(c1, user.email)
        assert c1.post("/api/auth/mfa/verify", {"code": code}).status_code == 204
        c2 = ApiClient()
        _password_step(c2, user.email)
        assert c2.post("/api/auth/mfa/verify", {"code": code}).status_code == 401

    def test_mfa_cookie_is_short_lived_and_typed(self, world: World, client: ApiClient) -> None:
        # An access token cannot be used as an MFA-pending token and vice versa.
        _password_step(client, world.a.operator.email)
        mfa = client.http.cookies.get(cookie_name(MFA), path="/api/auth")
        assert mfa
        other = ApiClient()
        other.http.cookies.set(cookie_name(ACCESS), mfa, path="/api")
        assert other.get("/api/auth/me").status_code == 401

    def test_recovery_code_login_single_use(self, world: World, client: ApiClient) -> None:
        user = make_user(world.a.id, Role.operator, "fresh@test.local", mfa=False)
        _password_step(client, user.email)
        start = client.post("/api/auth/mfa/enroll/start").json()
        secret = pyotp.parse_uri(start["otpauth_uri"]).secret
        r = client.post("/api/auth/mfa/enroll/confirm", {"code": pyotp.TOTP(secret).now()})
        codes = r.json()["recovery_codes"]
        assert len(codes) == 8 and len(set(codes)) == 8

        c2 = ApiClient()
        _password_step(c2, user.email)
        assert c2.post("/api/auth/mfa/verify", {"recovery_code": codes[0]}).status_code == 204
        c3 = ApiClient()
        _password_step(c3, user.email)
        assert c3.post("/api/auth/mfa/verify", {"recovery_code": codes[0]}).status_code == 401
        assert "auth.mfa.recovery_code_used" in audit_actions(world.a.id)
        with admin_conn() as conn:
            hashes = conn.execute(
                "SELECT code_hash FROM recovery_codes WHERE user_id = %s", (user.id,)
            ).fetchall()
        assert all(h[0].startswith("$argon2id$") for h in hashes)
        assert not any(codes[0].replace("-", "") in h[0] for h in hashes)


class TestEnrollment:
    def test_first_login_requires_enrollment(self, world: World, client: ApiClient) -> None:
        user = make_user(world.a.id, Role.operator, "new@test.local", mfa=False)
        r = _password_step(client, user.email)
        assert r.json()["enrollment_required"] is True
        # The regular MFA endpoint refuses a not-yet-enrolled account.
        assert client.post("/api/auth/mfa/verify", {"code": "123456"}).status_code == 401
        start = client.post("/api/auth/mfa/enroll/start")
        assert start.status_code == 200
        body = start.json()
        assert body["qr_svg_data_uri"].startswith("data:image/svg+xml;base64,")
        assert body["otpauth_uri"].startswith("otpauth://totp/")
        secret = pyotp.parse_uri(body["otpauth_uri"]).secret
        assert client.post("/api/auth/mfa/enroll/confirm", {"code": "000000"}).status_code == 401
        reset_totp_step(user.id)
        r = client.post("/api/auth/mfa/enroll/confirm", {"code": pyotp.TOTP(secret).now()})
        assert r.status_code == 200
        assert client.get("/api/auth/me").status_code == 200
        with admin_conn() as conn:
            row = conn.execute(
                "SELECT totp_secret_enc FROM users WHERE id = %s", (user.id,)
            ).fetchone()
        assert row and secret.encode() not in bytes(row[0])

    def test_enrolled_user_cannot_re_enroll(self, world: World, client: ApiClient) -> None:
        _password_step(client, world.a.operator.email)
        assert client.post("/api/auth/mfa/enroll/start").status_code == 401


class TestBruteForce:
    def test_progressive_lockout(self, world: World, client: ApiClient) -> None:
        user = world.a.operator
        for _ in range(5):
            assert _password_step(client, user.email, "Wrong-password-123").status_code == 401
        # Even the correct password is now refused, with the same generic answer.
        r = _password_step(client, user.email)
        assert r.status_code == 401 and r.json() == {"detail": "Invalid credentials"}
        assert "auth.login.locked" in audit_actions(world.a.id)
        with admin_conn() as conn:
            conn.execute(
                "UPDATE users SET locked_until = %s WHERE id = %s",
                (datetime.now(UTC) - timedelta(seconds=1), user.id),
            )
        assert _password_step(client, user.email).status_code == 200

    def test_mfa_failures_count_toward_lockout(self, world: World, client: ApiClient) -> None:
        user = world.a.operator
        _password_step(client, user.email)
        for _ in range(5):
            client.post("/api/auth/mfa/verify", {"code": "000000"})
        assert client.post("/api/auth/mfa/verify", {"code": user.totp()}).status_code == 401

    def test_rate_limit_per_account_also_for_unknown_accounts(
        self, client: ApiClient, world: World
    ) -> None:
        statuses = [_password_step(client, "ghost@test.local").status_code for _ in range(11)]
        assert statuses[:10] == [401] * 10 and statuses[10] == 429

    def test_rate_limit_per_ip(self, client: ApiClient, world: World) -> None:
        statuses = [_password_step(client, f"ghost{i}@test.local").status_code for i in range(31)]
        assert statuses[-1] == 429
        assert (
            int(
                client.post("/api/auth/login", {"email": "x@test.local", "password": "x"}).headers[
                    "retry-after"
                ]
            )
            > 0
        )


class TestSessions:
    def test_refresh_rotates_token(self, world: World, login: object) -> None:
        c = login(world.a.operator)  # type: ignore[operator]
        old = c.http.cookies.get(cookie_name(REFRESH), path="/api/auth")
        r = c.post("/api/auth/refresh")
        assert r.status_code == 204
        new = c.http.cookies.get(cookie_name(REFRESH), path="/api/auth")
        assert new and new != old
        assert c.get("/api/auth/me").status_code == 200

    def test_refresh_reuse_revokes_family(self, world: World, login: object) -> None:
        c = login(world.a.operator)  # type: ignore[operator]
        stolen = c.http.cookies.get(cookie_name(REFRESH), path="/api/auth")
        assert c.post("/api/auth/refresh").status_code == 204  # legitimate rotation
        attacker = ApiClient()
        attacker.http.cookies.set(cookie_name(REFRESH), stolen, path="/api/auth")
        assert attacker.post("/api/auth/refresh").status_code == 401
        # The legitimate client's session is revoked too (whole family).
        assert c.get("/api/auth/me").status_code == 401
        assert c.post("/api/auth/refresh").status_code == 401
        assert "auth.refresh.reuse_detected" in audit_actions(world.a.id)

    def test_refresh_tokens_stored_hashed(self, world: World, login: object) -> None:
        c = login(world.a.operator)  # type: ignore[operator]
        token = c.http.cookies.get(cookie_name(REFRESH), path="/api/auth")
        with admin_conn() as conn:
            rows = conn.execute("SELECT token_hash FROM refresh_tokens").fetchall()
        assert token and all(token not in r[0] for r in rows)

    def test_list_and_revoke_own_device(self, world: World, login: object) -> None:
        phone = login(world.a.operator)  # type: ignore[operator]
        laptop = login(world.a.operator)  # type: ignore[operator]
        sessions = laptop.get("/api/sessions").json()
        assert len([s for s in sessions if s["revoked_at"] is None]) == 2
        phone_id = phone.get("/api/auth/me").json()["session_id"]
        assert laptop.delete(f"/api/sessions/{phone_id}").status_code == 204
        assert phone.get("/api/auth/me").status_code == 401  # immediate, not after token expiry
        assert laptop.get("/api/auth/me").status_code == 200
        assert "auth.session.revoked" in audit_actions(world.a.id)

    def test_admin_revokes_user_session(self, world: World, login: object) -> None:
        victim = login(world.a.operator)  # type: ignore[operator]
        admin = login(world.a.admin)  # type: ignore[operator]
        sid = victim.get("/api/auth/me").json()["session_id"]
        r = admin.delete(f"/api/users/{world.a.operator.id}/sessions/{sid}")
        assert r.status_code == 204
        assert victim.get("/api/auth/me").status_code == 401

    def test_logout_revokes_session(self, world: World, login: object) -> None:
        c = login(world.a.operator)  # type: ignore[operator]
        refresh = c.http.cookies.get(cookie_name(REFRESH), path="/api/auth")
        assert c.post("/api/auth/logout").status_code == 204
        replay = ApiClient()
        replay.http.cookies.set(cookie_name(REFRESH), refresh, path="/api/auth")
        assert replay.post("/api/auth/refresh").status_code == 401
        assert "auth.logout" in audit_actions(world.a.id)

    def test_disabled_user_loses_access(self, world: World, login: object) -> None:
        victim = login(world.a.operator)  # type: ignore[operator]
        admin = login(world.a.admin)  # type: ignore[operator]
        r = admin.patch(f"/api/users/{world.a.operator.id}", {"is_active": False})
        assert r.status_code == 200
        assert victim.get("/api/auth/me").status_code == 401


class TestCsrf:
    def test_missing_token_rejected(self, world: World, login: object) -> None:
        c = login(world.a.operator)  # type: ignore[operator]
        aid = world.data["a"]["alerts"][0]
        r = c.http.post(f"/api/alerts/{aid}/confirm", headers={"Origin": ORIGIN})
        assert r.status_code == 403 and r.json()["detail"] == "CSRF validation failed"

    def test_wrong_token_rejected(self, world: World, login: object) -> None:
        c = login(world.a.operator)  # type: ignore[operator]
        aid = world.data["a"]["alerts"][0]
        r = c.http.post(f"/api/alerts/{aid}/confirm", headers={"X-CSRF-Token": "forged"})
        assert r.status_code == 403

    def test_foreign_origin_rejected(self, world: World, login: object) -> None:
        c = login(world.a.operator)  # type: ignore[operator]
        aid = world.data["a"]["alerts"][0]
        r = c.post(f"/api/alerts/{aid}/confirm", headers={"Origin": "https://evil.example"})
        assert r.status_code == 403

    def test_login_csrf_protected(self, world: World) -> None:
        c = ApiClient()
        r = c.http.post(
            "/api/auth/login", json={"email": world.a.operator.email, "password": PASSWORD}
        )
        assert r.status_code == 403


class TestReauth:
    def _make_stale(self, c: ApiClient) -> None:
        sid = c.get("/api/auth/me").json()["session_id"]
        with admin_conn() as conn:
            conn.execute(
                "UPDATE user_sessions SET mfa_verified_at = %s WHERE id = %s",
                (datetime.now(UTC) - timedelta(minutes=6), sid),
            )

    def test_sensitive_action_requires_fresh_mfa(self, world: World, login: object) -> None:
        admin = login(world.a.admin)  # type: ignore[operator]
        self._make_stale(admin)
        r = admin.post("/api/users/invitations", {"email": "x@test.local", "role": "operator"})
        assert r.status_code == 403 and r.json()["detail"] == "reauth_required"
        assert admin.post("/api/auth/reauth", {"code": "000000"}).status_code == 401
        assert admin.post("/api/auth/reauth", {"code": world.a.admin.totp()}).status_code == 204
        r = admin.post("/api/users/invitations", {"email": "x@test.local", "role": "operator"})
        assert r.status_code == 201
        assert "auth.reauth.success" in audit_actions(world.a.id)


class TestInvitations:
    def _invite(self, world: World, login: object, role: str = "operator") -> dict[str, str]:
        admin = login(world.a.admin)  # type: ignore[operator]
        r = admin.post("/api/users/invitations", {"email": "invitee@test.local", "role": role})
        assert r.status_code == 201, r.text
        return r.json()

    def test_accept_then_mandatory_enrollment(self, world: World, login: object) -> None:
        inv = self._invite(world, login)
        c = ApiClient()
        info = c.post("/api/auth/invitations/inspect", {"token": inv["token"]}).json()
        assert info["email"] == "invitee@test.local" and info["tenant_name"] == "Unit A"
        r = c.post(
            "/api/auth/invitations/accept",
            {
                "token": inv["token"],
                "display_name": "New Person",
                "password": "A-very-long-passphrase-9",
            },
        )
        assert r.status_code == 200 and r.json()["enrollment_required"] is True
        assert c.get("/api/auth/me").status_code == 401  # no session before MFA
        secret = pyotp.parse_uri(c.post("/api/auth/mfa/enroll/start").json()["otpauth_uri"]).secret
        assert (
            c.post("/api/auth/mfa/enroll/confirm", {"code": pyotp.TOTP(secret).now()}).status_code
            == 200
        )
        me = c.get("/api/auth/me").json()
        assert me["role"] == "operator" and me["tenant_id"] == str(world.a.id)
        assert "user.invitation.accepted" in audit_actions(world.a.id)

    def test_single_use(self, world: World, login: object) -> None:
        inv = self._invite(world, login)
        body = {
            "token": inv["token"],
            "display_name": "X Y",
            "password": "A-very-long-passphrase-9",
        }
        assert ApiClient().post("/api/auth/invitations/accept", body).status_code == 200
        assert ApiClient().post("/api/auth/invitations/accept", body).status_code == 401

    def test_expired(self, world: World, login: object) -> None:
        inv = self._invite(world, login)
        with admin_conn() as conn:
            conn.execute("UPDATE invitations SET expires_at = now() - interval '1 second'")
        body = {
            "token": inv["token"],
            "display_name": "X Y",
            "password": "A-very-long-passphrase-9",
        }
        assert ApiClient().post("/api/auth/invitations/accept", body).status_code == 401

    def test_token_stored_hashed_and_expires_in_24h(self, world: World, login: object) -> None:
        inv = self._invite(world, login)
        with admin_conn() as conn:
            row = conn.execute(
                "SELECT token_hash, expires_at - created_at FROM invitations"
            ).fetchone()
        assert row and row[0] != inv["token"] and inv["token"] not in row[0]
        assert timedelta(hours=23, minutes=59) < row[1] <= timedelta(hours=24, seconds=5)

    @pytest.mark.parametrize("password", ["short-pw-1", "password1234", "qwertyuiop123"])
    def test_password_policy(self, world: World, login: object, password: str) -> None:
        inv = self._invite(world, login)
        r = ApiClient().post(
            "/api/auth/invitations/accept",
            {"token": inv["token"], "display_name": "X Y", "password": password},
        )
        assert r.status_code == 422

    def test_only_admins_invite_and_no_role_escalation(self, world: World, login: object) -> None:
        op = login(world.a.operator)  # type: ignore[operator]
        assert (
            op.post(
                "/api/users/invitations", {"email": "z@test.local", "role": "operator"}
            ).status_code
            == 403
        )
        admin = login(world.a.admin)  # type: ignore[operator]
        r = admin.post("/api/users/invitations", {"email": "z@test.local", "role": "system_admin"})
        assert r.status_code == 403

    def test_no_public_registration_endpoint(self, client: ApiClient) -> None:
        for path in ("/api/auth/register", "/api/users", "/api/auth/signup"):
            assert client.post(path, {"email": "a@b.c", "password": "x" * 20}).status_code in (
                401,
                404,
                405,
            )


class TestSessionLimits:
    """Idle timeout (30 min) and absolute lifetime (12 h) are enforced by the server."""

    def _set(self, user_id: Any, **cols: str) -> None:
        with admin_conn() as conn:
            sets = ", ".join(f"{k} = {v}" for k, v in cols.items())
            conn.execute(f"UPDATE user_sessions SET {sets} WHERE user_id = %s", (user_id,))
            conn.commit()

    def test_idle_session_is_ended_and_cannot_come_back(self, world: World, login: Any) -> None:
        op = world.a.operator
        c = login(op)
        assert c.get("/api/auth/me").status_code == 200
        self._set(op.id, last_seen_at="now() - interval '31 minutes'")
        assert c.get("/api/auth/me").status_code == 401
        self._set(op.id, last_seen_at="now()")  # even a fresh timestamp cannot revive it
        assert c.get("/api/auth/me").status_code == 401
        with admin_conn() as conn:
            reason = conn.execute(
                "SELECT revoked_reason FROM user_sessions WHERE user_id = %s", (op.id,)
            ).fetchone()[0]
        assert reason == "idle_timeout"

    def test_activity_keeps_a_session_alive_and_refresh_respects_idle(
        self, world: World, login: Any
    ) -> None:
        op = world.a.operator
        c = login(op)
        self._set(op.id, last_seen_at="now() - interval '20 minutes'")
        assert c.get("/api/auth/me").status_code == 200  # within the idle window
        self._set(op.id, last_seen_at="now() - interval '40 minutes'")
        assert c.post("/api/auth/refresh").status_code == 401  # refresh does not bypass it

    def test_absolute_lifetime_is_twelve_hours(self, world: World, login: Any) -> None:
        login(world.a.operator)
        with admin_conn() as conn:
            hours = conn.execute(
                "SELECT extract(epoch FROM (expires_at - created_at)) / 3600 FROM user_sessions "
                "WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
                (world.a.operator.id,),
            ).fetchone()[0]
        assert 11.9 < float(hours) < 12.1
