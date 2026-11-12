"""Unit tests for envelope/field/file encryption, blind index and URL signing."""

from __future__ import annotations

import base64
import io
import os
import time
import uuid

import pytest

from app.core.crypto import (
    CryptoError,
    EnvKeyProvider,
    TenantKeyring,
    blind_index,
    decrypt_field,
    decrypt_stream,
    encrypt_field,
    encrypt_stream,
    field_key_version,
    generate_key,
    mask_plate,
    normalize_plate,
    sign_url_params,
    verify_url_params,
    wrap_aad,
)

T1, T2 = uuid.uuid4(), uuid.uuid4()


def keyring(tenant: uuid.UUID = T1, versions: int = 1) -> TenantKeyring:
    keys = {v: generate_key() for v in range(1, versions + 1)}
    return TenantKeyring(tenant, keys, versions, generate_key())


def b64key() -> str:
    return base64.b64encode(os.urandom(32)).decode()


class TestFieldEncryption:
    def test_round_trip(self) -> None:
        kr = keyring()
        blob = encrypt_field(kr, "alerts.plate", "B123ABC")
        assert b"B123ABC" not in blob
        assert decrypt_field(kr, "alerts.plate", blob) == "B123ABC"

    def test_random_nonce_gives_different_ciphertexts(self) -> None:
        kr = keyring()
        assert encrypt_field(kr, "f", "same") != encrypt_field(kr, "f", "same")

    @pytest.mark.parametrize("position", [7, 10, 20, -1])
    def test_modified_ciphertext_fails(self, position: int) -> None:
        kr = keyring()
        blob = bytearray(encrypt_field(kr, "alerts.plate", "B123ABC"))
        blob[position] ^= 0x01
        with pytest.raises(CryptoError):
            decrypt_field(kr, "alerts.plate", bytes(blob))

    def test_wrong_field_name_in_aad_fails(self) -> None:
        kr = keyring()
        blob = encrypt_field(kr, "alerts.plate", "B123ABC")
        with pytest.raises(CryptoError):
            decrypt_field(kr, "users.totp_secret", blob)

    def test_wrong_tenant_aad_fails_even_with_same_key(self) -> None:
        kr = keyring(T1)
        other = TenantKeyring(T2, kr.data_keys, kr.active_data_version, kr.index_key)
        blob = encrypt_field(kr, "alerts.plate", "B123ABC")
        with pytest.raises(CryptoError):
            decrypt_field(other, "alerts.plate", blob)

    def test_wrong_tenant_key_fails(self) -> None:
        blob = encrypt_field(keyring(T1), "alerts.plate", "B123ABC")
        with pytest.raises(CryptoError):
            decrypt_field(keyring(T1), "alerts.plate", blob)

    def test_key_version_is_stored_and_old_versions_still_decrypt(self) -> None:
        kr1 = keyring(versions=1)
        old = encrypt_field(kr1, "f", "old value")
        kr2 = TenantKeyring(T1, {**kr1.data_keys, 2: generate_key()}, 2, kr1.index_key)
        new = encrypt_field(kr2, "f", "new value")
        assert field_key_version(old) == 1
        assert field_key_version(new) == 2
        assert decrypt_field(kr2, "f", old) == "old value"
        assert decrypt_field(kr2, "f", new) == "new value"

    def test_unknown_version_fails(self) -> None:
        blob = encrypt_field(keyring(versions=2), "f", "x")
        with pytest.raises(CryptoError):
            decrypt_field(keyring(versions=1), "f", blob)

    def test_garbage_is_rejected(self) -> None:
        with pytest.raises(CryptoError):
            decrypt_field(keyring(), "f", b"not a ciphertext")


class TestBlindIndex:
    def test_deterministic_per_tenant_and_normalized(self) -> None:
        kr = keyring()
        a = blind_index(kr, "alerts.plate", normalize_plate("b 123-abc"))
        b = blind_index(kr, "alerts.plate", normalize_plate("B123ABC"))
        assert a == b and len(a) == 32

    def test_differs_across_tenants(self) -> None:
        assert blind_index(keyring(T1), "p", "B123ABC") != blind_index(keyring(T2), "p", "B123ABC")

    def test_mask(self) -> None:
        assert mask_plate("B 123 ABC") == "B*****C"


class TestEnvelope:
    def test_wrap_unwrap_and_rotation(self) -> None:
        k1, k2 = b64key(), b64key()
        p1 = EnvKeyProvider(f"1:{k1}", 1)
        dek = generate_key()
        aad = wrap_aad(T1, "data", 1)
        wrapped, mv = p1.wrap(dek, aad)
        assert mv == 1 and dek not in wrapped
        p2 = EnvKeyProvider(f"1:{k1},2:{k2}", 2)
        assert p2.unwrap(wrapped, 1, aad) == dek  # old master version still readable
        rewrapped, mv2 = p2.wrap(dek, aad)
        assert mv2 == 2 and p2.unwrap(rewrapped, 2, aad) == dek

    def test_wrong_aad_or_master_fails(self) -> None:
        p = EnvKeyProvider(f"1:{b64key()}", 1)
        wrapped, _ = p.wrap(generate_key(), wrap_aad(T1, "data", 1))
        with pytest.raises(CryptoError):
            p.unwrap(wrapped, 1, wrap_aad(T2, "data", 1))  # DEK row copied to another tenant
        with pytest.raises(CryptoError):
            EnvKeyProvider(f"1:{b64key()}", 1).unwrap(wrapped, 1, wrap_aad(T1, "data", 1))

    def test_rejects_bad_config(self) -> None:
        with pytest.raises(ValueError):
            EnvKeyProvider("1:" + base64.b64encode(b"short").decode(), 1)
        with pytest.raises(ValueError):
            EnvKeyProvider(f"1:{b64key()}", 2)


class TestFileEncryption:
    @pytest.mark.parametrize("size", [0, 1, 1000, 4096, 4097, 3 * 4096])
    def test_round_trip(self, size: int) -> None:
        kr, ev = keyring(), uuid.uuid4()
        data = os.urandom(size)
        out = io.BytesIO()
        assert encrypt_stream(kr, ev, io.BytesIO(data), out, chunk_size=4096) == size
        if size >= 16:  # a 1-byte plaintext can appear in random ciphertext by chance
            assert data[:64] not in out.getvalue()
        out.seek(0)
        assert b"".join(decrypt_stream(kr, ev, out)) == data

    def _encrypted(self, kr: TenantKeyring, ev: uuid.UUID, size: int = 3 * 4096) -> bytes:
        out = io.BytesIO()
        encrypt_stream(kr, ev, io.BytesIO(os.urandom(size)), out, chunk_size=4096)
        return out.getvalue()

    def test_tamper_detected(self) -> None:
        kr, ev = keyring(), uuid.uuid4()
        blob = bytearray(self._encrypted(kr, ev))
        blob[100] ^= 0xFF
        with pytest.raises(CryptoError):
            b"".join(decrypt_stream(kr, ev, io.BytesIO(bytes(blob))))

    def test_truncation_detected(self) -> None:
        kr, ev = keyring(), uuid.uuid4()
        blob = self._encrypted(kr, ev)
        chunk = 4096 + 16
        truncated = blob[: 44 + 2 * chunk]  # drop the final chunk at a chunk boundary
        with pytest.raises(CryptoError):
            b"".join(decrypt_stream(kr, ev, io.BytesIO(truncated)))

    def test_chunk_reorder_detected(self) -> None:
        kr, ev = keyring(), uuid.uuid4()
        blob = self._encrypted(kr, ev)
        header, c = blob[:44], 4096 + 16
        chunks = [blob[44 + i * c : 44 + (i + 1) * c] for i in range(3)]
        swapped = header + chunks[1] + chunks[0] + chunks[2]
        with pytest.raises(CryptoError):
            b"".join(decrypt_stream(kr, ev, io.BytesIO(swapped)))

    def test_wrong_evidence_id_or_tenant_fails(self) -> None:
        kr, ev = keyring(), uuid.uuid4()
        blob = self._encrypted(kr, ev)
        with pytest.raises(CryptoError):
            b"".join(decrypt_stream(kr, uuid.uuid4(), io.BytesIO(blob)))
        with pytest.raises(CryptoError):
            b"".join(decrypt_stream(keyring(T2), ev, io.BytesIO(blob)))


class TestSignedUrls:
    KEY = os.urandom(32)

    def test_valid(self) -> None:
        exp = int(time.time()) + 60
        sig = sign_url_params(self.KEY, "view", "ev:redacted", "user-1", exp)
        assert verify_url_params(self.KEY, "view", "ev:redacted", "user-1", exp, sig)

    def test_expired(self) -> None:
        exp = int(time.time()) - 1
        sig = sign_url_params(self.KEY, "view", "ev", "u", exp)
        assert not verify_url_params(self.KEY, "view", "ev", "u", exp, sig)

    @pytest.mark.parametrize("field", ["purpose", "resource", "user", "exp", "sig", "key"])
    def test_any_change_invalidates(self, field: str) -> None:
        exp = int(time.time()) + 60
        args = {"purpose": "view", "resource": "ev:redacted", "user": "u1", "exp": exp}
        sig = sign_url_params(self.KEY, args["purpose"], args["resource"], args["user"], exp)
        key = self.KEY
        if field == "sig":
            sig = sig[:-1] + ("A" if sig[-1] != "A" else "B")
        elif field == "key":
            key = os.urandom(32)
        elif field == "exp":
            args["exp"] = exp + 30
        else:
            args[field] = "other"
        assert not verify_url_params(
            key,
            args["purpose"],
            args["resource"],
            args["user"],
            args["exp"],
            sig,  # type: ignore[arg-type]
        )
