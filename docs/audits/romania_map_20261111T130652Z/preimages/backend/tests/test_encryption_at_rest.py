"""Encryption at rest (DB + evidence files), key rotation, signed evidence URLs, log redaction."""

from __future__ import annotations

import base64
import logging
import os
import time
from pathlib import Path
from typing import Any

import pytest

from app.config import get_settings
from app.core.crypto import CryptoError, decrypt_field, field_key_version, sign_url_params
from app.core.redaction import REDACTED, RedactingFilter, redact
from app.db import tenant_session
from app.models import Alert, Evidence
from app.services import keys as key_service
from tests.conftest import EVIDENCE_DIR, World, admin_conn


class TestCiphertextAtRest:
    def test_plates_and_totp_secrets_are_ciphertext_in_db(self, world: World) -> None:
        with admin_conn() as conn:
            blobs = [bytes(r[0]) for r in conn.execute("SELECT plate_enc FROM alerts").fetchall()]
            dump = b"".join(blobs) + b"".join(
                bytes(r[0]) for r in conn.execute("SELECT wrapped_key FROM tenant_keys").fetchall()
            )
        for plate in world.data["a"]["plates"] + world.data["b"]["plates"]:
            assert plate.encode() not in dump
        assert all(b[:2] == b"F1" for b in blobs)

    def test_evidence_files_are_ciphertext_on_disk(self, world: World) -> None:
        files = list(EVIDENCE_DIR.rglob("*.enc"))
        assert len(files) >= 4
        for f in files:
            data = f.read_bytes()
            assert data[:4] == b"RSE1" and b"\x89PNG" not in data and b"IHDR" not in data

    def test_copying_a_tenant_key_row_to_another_tenant_does_not_unwrap(self, world: World) -> None:
        with admin_conn() as conn:
            conn.execute(
                "UPDATE tenant_keys SET wrapped_key = (SELECT wrapped_key FROM tenant_keys "
                "WHERE tenant_id = %s AND purpose = 'data' AND version = 1) "
                "WHERE tenant_id = %s AND purpose = 'data' AND version = 1",
                (world.a.id, world.b.id),
            )
        with tenant_session(world.b.id) as db, pytest.raises(CryptoError):
            key_service.load_keyring(db, world.b.id)


class TestKeyRotation:
    def test_rotate_tenant_key_reencrypts_and_keeps_old_evidence_readable(
        self, world: World
    ) -> None:
        tid = world.a.id
        with tenant_session(tid) as db:
            new_version = key_service.rotate_data_key(db, tid)
            db.commit()
            kr = key_service.load_keyring(db, tid)
            assert new_version == 2 and kr.active_data_version == 2 and set(kr.data_keys) == {1, 2}
            alerts = db.query(Alert).all()
            assert all(a.plate_enc and field_key_version(a.plate_enc) == 2 for a in alerts)
            plates = {decrypt_field(kr, "alerts.plate", a.plate_enc) for a in alerts if a.plate_enc}
            assert plates == set(world.data["a"]["plates"])
            from app.services.evidence import open_decrypted

            ev = db.get(Evidence, world.data["a"]["evidence"])
            assert ev is not None and ev.key_version == 1
            assert b"".join(open_decrypted(kr, ev, "original")).startswith(b"\x89PNG")
        # Unit B is untouched.
        with tenant_session(world.b.id) as db:
            assert key_service.load_keyring(db, world.b.id).active_data_version == 1

    def test_rewrap_under_new_master_key(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        old_spec = get_settings().master_keys.get_secret_value()
        new_key = base64.b64encode(os.urandom(32)).decode()
        settings = get_settings()
        monkeypatch.setattr(
            settings, "master_keys", type(settings.master_keys)(f"{old_spec},2:{new_key}")
        )
        monkeypatch.setattr(settings, "master_key_current", 2)
        key_service.get_key_provider.cache_clear()
        try:
            with tenant_session(world.a.id) as db:
                before = key_service.load_keyring(db, world.a.id)
                assert key_service.rewrap_tenant_keys(db, world.a.id) == 2
                db.commit()
            with admin_conn() as conn:
                versions = {
                    r[0]
                    for r in conn.execute(
                        "SELECT master_key_version FROM tenant_keys WHERE tenant_id = %s",
                        (world.a.id,),
                    ).fetchall()
                }
            assert versions == {2}
            # Drop the old master key entirely: data must still decrypt (DEKs unchanged).
            monkeypatch.setattr(settings, "master_keys", type(settings.master_keys)(f"2:{new_key}"))
            key_service.get_key_provider.cache_clear()
            with tenant_session(world.a.id) as db:
                after = key_service.load_keyring(db, world.a.id)
            assert after.data_keys == before.data_keys
        finally:
            key_service.get_key_provider.cache_clear()

    def test_rotate_endpoint_requires_admin_and_is_audited(self, world: World, login: Any) -> None:
        assert login(world.a.operator).post("/api/tenants/current/rotate-key").status_code == 403
        r = login(world.a.admin).post("/api/tenants/current/rotate-key")
        assert r.status_code == 200 and r.json()["new_data_key_version"] == 2
        from tests.conftest import audit_actions

        assert "crypto.key_rotated" in audit_actions(world.a.id)


class TestSignedEvidenceUrls:
    def test_redacted_view_works_with_signed_url(self, world: World, login: Any) -> None:
        c = login(world.a.operator)
        ev = world.data["a"]["evidence"]
        url = c.post(f"/api/evidence/{ev}/access", {"variant": "redacted"}).json()["url"]
        r = c.get(url)
        assert r.status_code == 200 and r.content.startswith(b"\x89PNG")
        assert r.headers["cache-control"] == "no-store"
        assert "exp=" in url and "sig=" in url

    def test_original_requires_grant(self, world: World, login: Any) -> None:
        c = login(world.a.operator)
        r = c.post(f"/api/evidence/{world.data['a']['evidence']}/access", {"variant": "original"})
        assert r.status_code == 403

    def test_url_bound_to_user(self, world: World, login: Any) -> None:
        ev = world.data["a"]["evidence"]
        url = (
            login(world.a.operator)
            .post(f"/api/evidence/{ev}/access", {"variant": "redacted"})
            .json()["url"]
        )
        assert login(world.a.admin).get(url).status_code == 403  # same tenant, other user

    def test_url_requires_session(self, world: World, login: Any) -> None:
        from tests.conftest import ApiClient

        ev = world.data["a"]["evidence"]
        url = (
            login(world.a.operator)
            .post(f"/api/evidence/{ev}/access", {"variant": "redacted"})
            .json()["url"]
        )
        assert ApiClient().get(url).status_code == 401

    def test_expired_and_tampered_urls_rejected(self, world: World, login: Any) -> None:
        c = login(world.a.operator)
        ev = world.data["a"]["evidence"]
        key = get_settings().url_signing_key.get_secret_value().encode()
        uid = str(world.a.operator.id)
        exp = int(time.time()) - 1
        sig = sign_url_params(key, "view", f"{ev}:redacted", uid, exp)
        assert (
            c.get(
                f"/api/evidence/{ev}/content?variant=redacted&purpose=view&exp={exp}&sig={sig}"
            ).status_code
            == 403
        )
        exp = int(time.time()) + 60
        sig = sign_url_params(key, "view", f"{ev}:redacted", uid, exp)
        # Upgrading the variant in a redacted link must fail.
        assert (
            c.get(
                f"/api/evidence/{ev}/content?variant=original&purpose=view&exp={exp}&sig={sig}"
            ).status_code
            == 403
        )
        assert (
            c.get(
                f"/api/evidence/{ev}/content?variant=redacted&purpose=view"
                f"&exp={exp + 100}&sig={sig}"
            ).status_code
            == 403
        )

    def test_ttl_is_60_seconds(self, world: World, login: Any) -> None:
        c = login(world.a.operator)
        url = c.post(
            f"/api/evidence/{world.data['a']['evidence']}/access", {"variant": "redacted"}
        ).json()["url"]
        exp = int(url.split("exp=")[1].split("&")[0])
        assert 55 <= exp - time.time() <= 61

    def test_tampered_file_is_not_served(self, world: World, login: Any) -> None:
        c = login(world.a.operator)
        ev = world.data["a"]["evidence"]
        with admin_conn() as conn:
            rel = conn.execute(
                "SELECT redacted_path FROM evidence WHERE id = %s", (ev,)
            ).fetchone()[0]
        path = Path(EVIDENCE_DIR) / rel
        blob = bytearray(path.read_bytes())
        blob[60] ^= 0xFF
        path.write_bytes(bytes(blob))
        url = c.post(f"/api/evidence/{ev}/access", {"variant": "redacted"}).json()["url"]
        assert c.get(url).status_code == 500


class TestLogRedaction:
    def test_structures(self) -> None:
        out = redact(
            {"password": "p", "nested": {"refresh_token": "t", "plate": "B1"}, "session_id": "s"}
        )
        assert out == {
            "password": REDACTED,
            "nested": {"refresh_token": REDACTED, "plate": REDACTED},
            "session_id": "s",
        }

    @pytest.mark.parametrize(
        "message",
        [
            "login password=hunter2hunter2 for x",
            'payload {"password": "hunter2hunter2"}',
            "Authorization: Bearer abc.def.ghi-secret",
            "token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJlLXNlY3JldA",
            "Cookie: __Secure-rs_access=hunter2hunter2; other=1",
            "plate=B123XYZ detected",
            "RS_MASTER_KEYS=1:hunter2hunter2",
        ],
    )
    def test_filter_scrubs_messages(self, message: str, caplog: pytest.LogCaptureFixture) -> None:
        logger = logging.getLogger("app.test")
        logger.addFilter(RedactingFilter())
        with caplog.at_level(logging.INFO, logger="app.test"):
            logger.info(message)
            logger.info("args %s", message)
        text = caplog.text
        for secret in ("hunter2hunter2", "c2lnbmF0dXJlLXNlY3JldA", "abc.def.ghi-secret", "B123XYZ"):
            assert secret not in text
        assert REDACTED in text

    def test_validation_errors_do_not_echo_input(self, world: World, client: Any) -> None:
        r = client.post("/api/auth/login", {"email": "not-an-email", "password": "hunter2hunter2"})
        assert r.status_code == 422 and "hunter2hunter2" not in r.text
