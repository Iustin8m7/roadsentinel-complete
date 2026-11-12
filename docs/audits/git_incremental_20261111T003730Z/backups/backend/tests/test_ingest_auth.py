"""HMAC authentication of the detection pipeline and management of its keys."""

from __future__ import annotations

import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.core.rate_limit import get_rate_limiter
from app.db import tenant_session
from app.models import ServiceKey
from app.services import ingest_auth
from app.services.keys import load_keyring
from tests.conftest import ORIGIN, World, admin_conn, audit_actions

PING = "/api/ingest/ping"


class Pipeline:
    """What the pipeline's sink does: sign the exact bytes sent."""

    def __init__(self, key_id: str, secret: str) -> None:
        from app.main import create_app

        self.key_id, self.secret = key_id, secret
        self.http = TestClient(create_app(), base_url=ORIGIN, raise_server_exceptions=False)

    def headers(
        self,
        method: str,
        target: str,
        body: bytes,
        *,
        ts: int | None = None,
        nonce: str | None = None,
    ) -> dict[str, str]:
        ts_s = str(int(time.time()) if ts is None else ts)
        nonce = nonce or secrets.token_urlsafe(18)
        sig = ingest_auth.sign(
            self.secret, ingest_auth.signing_message(method, target, ts_s, nonce, body)
        )
        return {
            "X-RS-Key-Id": self.key_id,
            "X-RS-Timestamp": ts_s,
            "X-RS-Nonce": nonce,
            "X-RS-Signature": sig,
        }

    def post(
        self,
        target: str = PING,
        body: bytes = b"{}",
        *,
        ts: int | None = None,
        nonce: str | None = None,
        headers: dict[str, str] | None = None,
        send_body: bytes | None = None,
        send_target: str | None = None,
    ) -> Any:
        h = {**self.headers("POST", target, body, ts=ts, nonce=nonce), **(headers or {})}
        return self.http.post(
            send_target or target,
            content=body if send_body is None else send_body,
            follow_redirects=False,
            headers={"Content-Type": "application/json", **h},
        )


def make_pipeline(
    tenant_id: uuid.UUID, name: str = "pipeline-1", camera_ids: list[uuid.UUID] | None = None
) -> tuple[Pipeline, uuid.UUID]:
    with tenant_session(tenant_id) as db:
        account = ingest_auth.create_account(db, tenant_id, name, camera_ids=camera_ids)
        issued = ingest_auth.issue_key(db, load_keyring(db, tenant_id), account)
        db.commit()
        return Pipeline(issued.key_id, issued.secret), account.id


@pytest.fixture
def pipe(world: World) -> Pipeline:
    return make_pipeline(world.a.id)[0]


class TestSignedRequests:
    def test_valid_signature_is_accepted(self, pipe: Pipeline) -> None:
        r = pipe.post()
        assert r.status_code == 200, r.text
        assert r.json() == {"ok": True, "account": "pipeline-1"}

    def test_no_csrf_token_or_cookie_needed(self, pipe: Pipeline) -> None:
        assert pipe.http.cookies.get("__Secure-rs_csrf") is None
        assert pipe.post().status_code == 200

    def test_tenant_comes_only_from_the_key(self, world: World) -> None:
        a, _ = make_pipeline(world.a.id, "pipe-a")
        b, _ = make_pipeline(world.b.id, "pipe-b")
        assert a.post().json()["account"] == "pipe-a"
        assert b.post().json()["account"] == "pipe-b"
        assert "ingest.auth.failure" not in audit_actions(world.a.id)

    @pytest.mark.parametrize(
        "mutate",
        [
            pytest.param({"send_body": b'{"x":1}'}, id="body-tampered"),
            pytest.param({"send_target": PING + "?a=1"}, id="query-added"),
            pytest.param({"send_target": "/api/ingest/ping/"}, id="path-changed"),
        ],
    )
    def test_tampered_request_is_rejected(self, pipe: Pipeline, mutate: dict[str, Any]) -> None:
        r = pipe.post(**mutate)
        assert r.status_code in (401, 404, 307), r.text
        assert r.status_code != 200

    def test_wrong_method_is_part_of_the_signature(self, pipe: Pipeline) -> None:
        h = pipe.headers("DELETE", PING, b"{}")
        r = pipe.http.post(PING, content=b"{}", headers=h)
        assert r.status_code == 401

    def test_forged_signature(self, pipe: Pipeline) -> None:
        other = Pipeline(pipe.key_id, secrets.token_urlsafe(32))
        assert other.post().status_code == 401

    def test_unknown_key(self, pipe: Pipeline) -> None:
        ghost = Pipeline("rsk_" + secrets.token_urlsafe(12), pipe.secret)
        assert ghost.post().status_code == 401

    def test_all_failures_look_the_same(self, pipe: Pipeline) -> None:
        bad = [
            Pipeline(pipe.key_id, "wrong-secret-value-0000000000000000000").post(),
            Pipeline("rsk_" + secrets.token_urlsafe(12), pipe.secret).post(),
            pipe.post(ts=int(time.time()) - 3600),
            pipe.post(headers={"X-RS-Signature": "!!!"}),
        ]
        assert {r.status_code for r in bad} == {401}
        assert len({r.text for r in bad}) == 1

    @pytest.mark.parametrize(
        "header", ["X-RS-Key-Id", "X-RS-Timestamp", "X-RS-Nonce", "X-RS-Signature"]
    )
    def test_missing_header(self, pipe: Pipeline, header: str) -> None:
        h = pipe.headers("POST", PING, b"{}")
        del h[header]
        assert pipe.http.post(PING, content=b"{}", headers=h).status_code == 401

    def test_missing_headers_entirely(self, pipe: Pipeline) -> None:
        assert pipe.http.post(PING, content=b"{}").status_code == 401

    def test_session_cookie_is_not_accepted(self, world: World, login: Any) -> None:
        client = login(world.a.admin)
        r = client.post(PING, {})
        assert r.status_code == 401


class TestReplayAndClock:
    def test_replayed_request_is_rejected_and_audited(self, world: World, pipe: Pipeline) -> None:
        ts, nonce = int(time.time()), secrets.token_urlsafe(18)
        assert pipe.post(ts=ts, nonce=nonce).status_code == 200
        assert pipe.post(ts=ts, nonce=nonce).status_code == 401
        assert "ingest.auth.replay" in audit_actions(world.a.id)

    def test_same_nonce_is_independent_per_key(self, world: World) -> None:
        a, _ = make_pipeline(world.a.id, "a")
        b, _ = make_pipeline(world.b.id, "b")
        ts, nonce = int(time.time()), secrets.token_urlsafe(18)
        assert a.post(ts=ts, nonce=nonce).status_code == 200
        assert b.post(ts=ts, nonce=nonce).status_code == 200

    def test_old_timestamp(self, pipe: Pipeline) -> None:
        skew = get_settings().ingest_clock_skew_seconds
        assert pipe.post(ts=int(time.time()) - skew - 5).status_code == 401

    def test_future_timestamp(self, pipe: Pipeline) -> None:
        skew = get_settings().ingest_clock_skew_seconds
        assert pipe.post(ts=int(time.time()) + skew + 5).status_code == 401

    def test_unsigned_attempts_do_not_burn_nonces(self, pipe: Pipeline) -> None:
        nonce = secrets.token_urlsafe(18)
        forged = Pipeline(pipe.key_id, "forged-secret-000000000000000000000")
        assert forged.post(nonce=nonce).status_code == 401
        assert pipe.post(nonce=nonce).status_code == 200

    def test_expired_nonces_can_be_purged(self, world: World, pipe: Pipeline) -> None:
        assert pipe.post(ts=int(time.time()) - 50).status_code == 200
        with admin_conn() as conn:
            conn.execute("UPDATE ingest_nonces SET expires_at = now() - interval '1 minute'")
        with tenant_session(world.a.id) as db:
            assert ingest_auth.purge_expired_nonces(db) == 1
            db.commit()


class TestKeyLifecycle:
    def test_revoked_key_stops_working_immediately(self, world: World) -> None:
        pipe, account_id = make_pipeline(world.a.id)
        assert pipe.post().status_code == 200
        with tenant_session(world.a.id) as db:
            account = db.get(ingest_auth.ServiceAccount, account_id)
            assert account and ingest_auth.revoke_key(db, account, pipe.key_id)
            db.commit()
        assert pipe.post().status_code == 401
        assert "ingest.auth.failure" in audit_actions(world.a.id)

    def test_deactivated_account(self, world: World) -> None:
        pipe, account_id = make_pipeline(world.a.id)
        with tenant_session(world.a.id) as db:
            account = db.get(ingest_auth.ServiceAccount, account_id)
            assert account
            account.is_active = False
            db.commit()
        assert pipe.post().status_code == 401

    def test_rotation_keeps_old_key_for_the_overlap_only(self, world: World) -> None:
        old, account_id = make_pipeline(world.a.id)
        with tenant_session(world.a.id) as db:
            account = db.get(ingest_auth.ServiceAccount, account_id)
            assert account
            issued = ingest_auth.issue_key(
                db, load_keyring(db, world.a.id), account, overlap_seconds=3600
            )
            db.commit()
        new = Pipeline(issued.key_id, issued.secret)
        assert old.post().status_code == 200
        assert new.post().status_code == 200
        with admin_conn() as conn:
            conn.execute(
                "UPDATE service_keys SET expires_at = now() - interval '1 second' "
                "WHERE key_id = %s",
                (old.key_id,),
            )
        assert old.post().status_code == 401
        assert new.post().status_code == 200

    def test_at_most_two_live_keys(self, world: World) -> None:
        _, account_id = make_pipeline(world.a.id)
        with tenant_session(world.a.id) as db:
            account = db.get(ingest_auth.ServiceAccount, account_id)
            assert account
            keyring = load_keyring(db, world.a.id)
            ingest_auth.issue_key(db, keyring, account)
            with pytest.raises(ValueError):
                ingest_auth.issue_key(db, keyring, account)

    def test_secret_is_encrypted_at_rest(self, world: World) -> None:
        pipe, _ = make_pipeline(world.a.id)
        with admin_conn() as conn:
            (blob,) = conn.execute(
                "SELECT secret_enc FROM service_keys WHERE key_id = %s", (pipe.key_id,)
            ).fetchone()
        assert pipe.secret.encode() not in bytes(blob)

    def test_secret_is_not_loggable_via_audit_details(self, world: World) -> None:
        pipe, _ = make_pipeline(world.a.id)
        pipe.post(headers={"X-RS-Signature": "x" * 43})
        with admin_conn() as conn:
            rows = conn.execute("SELECT details::text FROM audit_log").fetchall()
        assert not any(pipe.secret in r[0] for r in rows)

    def test_key_rows_are_tenant_isolated(self, world: World) -> None:
        pipe, _ = make_pipeline(world.a.id)
        with tenant_session(world.b.id) as db:
            from sqlalchemy import select

            assert db.scalars(select(ServiceKey)).all() == []
        assert pipe.key_id


class TestLimits:
    def test_rate_limit_per_key(self, world: World, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(get_settings(), "ingest_requests_per_minute", 3)
        pipe, _ = make_pipeline(world.a.id)
        codes = [pipe.post().status_code for _ in range(5)]
        assert codes[:3] == [200, 200, 200]
        assert codes[3:] == [429, 429]
        assert "ingest.rate_limited" in audit_actions(world.a.id)

    def test_repeated_failures_are_throttled(self, pipe: Pipeline) -> None:
        get_rate_limiter().reset()
        forged = Pipeline(pipe.key_id, "forged-secret-000000000000000000000")
        codes = [forged.post().status_code for _ in range(35)]
        assert 429 in codes

    def test_oversized_body_is_refused_before_hashing(
        self, pipe: Pipeline, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(get_settings(), "ingest_max_body_bytes", 100)
        assert pipe.post(body=b"x" * 500).status_code == 413


class TestManagementApi:
    def test_admin_creates_account_and_key_secret_shown_once(
        self, world: World, login: Any
    ) -> None:
        admin = login(world.a.admin)
        r = admin.post("/api/service-accounts", {"name": "edge-1"})
        assert r.status_code == 201, r.text
        account = r.json()
        assert account["keys"] == []
        r = admin.post(f"/api/service-accounts/{account['id']}/keys")
        assert r.status_code == 201, r.text
        issued = r.json()
        assert Pipeline(issued["key_id"], issued["secret"]).post().status_code == 200
        listing = admin.get("/api/service-accounts").json()
        assert issued["secret"] not in str(listing)
        assert listing[0]["keys"][0]["key_id"] == issued["key_id"]
        actions = audit_actions(world.a.id)
        assert "service.account.created" in actions and "service.key.issued" in actions

    def test_revoke_via_api(self, world: World, login: Any) -> None:
        admin = login(world.a.admin)
        acct = admin.post("/api/service-accounts", {"name": "edge-2"}).json()
        issued = admin.post(f"/api/service-accounts/{acct['id']}/keys").json()
        pipe = Pipeline(issued["key_id"], issued["secret"])
        assert pipe.post().status_code == 200
        assert (
            admin.delete(f"/api/service-accounts/{acct['id']}/keys/{issued['key_id']}").status_code
            == 204
        )
        assert pipe.post().status_code == 401
        assert "service.key.revoked" in audit_actions(world.a.id)

    @pytest.mark.parametrize("role", ["operator", "patrol", "auditor"])
    def test_other_roles_are_forbidden(self, world: World, login: Any, role: str) -> None:
        from app.models import Role

        user = world.a.users[Role(role)]
        client = login(user)
        assert client.get("/api/service-accounts").status_code == 403
        assert client.post("/api/service-accounts", {"name": "nope"}).status_code == 403

    def test_unit_b_admin_cannot_see_or_touch_unit_a_accounts(
        self, world: World, login: Any
    ) -> None:
        pipe, account_id = make_pipeline(world.a.id)
        b_admin = login(world.b.admin)
        assert b_admin.get("/api/service-accounts").json() == []
        assert b_admin.post(f"/api/service-accounts/{account_id}/keys").status_code == 404
        assert (
            b_admin.delete(f"/api/service-accounts/{account_id}/keys/{pipe.key_id}").status_code
            == 404
        )
        assert (
            b_admin.patch(f"/api/service-accounts/{account_id}", {"is_active": False}).status_code
            == 404
        )
        assert pipe.post().status_code == 200
        assert "security.cross_tenant_access" in audit_actions(world.a.id)

    def test_camera_scope_must_belong_to_the_tenant(self, world: World, login: Any) -> None:
        admin = login(world.a.admin)
        r = admin.post(
            "/api/service-accounts",
            {"name": "edge-3", "camera_ids": [str(world.data["b"]["camera"])]},
        )
        assert r.status_code == 422
        ok = admin.post(
            "/api/service-accounts",
            {"name": "edge-3", "camera_ids": [str(world.data["a"]["camera"])]},
        )
        assert ok.status_code == 201

    def test_unknown_fields_are_rejected(self, world: World, login: Any) -> None:
        admin = login(world.a.admin)
        r = admin.post("/api/service-accounts", {"name": "edge-4", "tenant_id": str(world.b.id)})
        assert r.status_code == 422

    def test_sensitive_actions_need_fresh_mfa(self, world: World, login: Any) -> None:
        admin = login(world.a.admin)
        with admin_conn() as conn:
            conn.execute(
                "UPDATE user_sessions SET mfa_verified_at = %s",
                (datetime.now(UTC) - timedelta(hours=2),),
            )
        r = admin.post("/api/service-accounts", {"name": "stale"})
        assert r.status_code == 403 and "reauth_required" in r.text
