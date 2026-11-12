"""Envelope encryption, field-level encryption, blind indexes, file encryption and URL signing.

All primitives come from ``cryptography`` (AES-256-GCM, HKDF-SHA256, HMAC-SHA256). Nothing here
invents a cipher; this module only fixes formats and associated data.

Key hierarchy::

    master key (env / future KMS, versioned)  --wraps-->  per-tenant DEK (versioned, 256-bit)
                                                          per-tenant index key (HMAC)

Field ciphertext format (bytes)::

    b"F1" | dek_version (4, big endian) | nonce (12) | AES-GCM ciphertext+tag
    AAD = b"rs-field|" + tenant_id + b"|" + field name

Evidence file format::

    header: b"RSE1" | dek_version (4) | salt (32) | chunk_size (4)
    chunks: [ciphertext+tag] ... ; per-file key = HKDF(DEK, salt, info=tenant|evidence)
    nonce(i) = 4 zero bytes | i (8, big endian); AAD = header | i | final flag
    The final flag makes truncation detectable; the header in the AAD makes it tamper-evident.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import BinaryIO

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

KEY_BYTES = 32
NONCE_BYTES = 12
FIELD_MAGIC = b"F1"
FILE_MAGIC = b"RSE1"
FILE_SALT_BYTES = 32
DEFAULT_CHUNK_SIZE = 64 * 1024
TAG_BYTES = 16


class CryptoError(Exception):
    """Raised for any decryption/verification failure. Deliberately carries no detail."""


# --------------------------------------------------------------------------- key providers


class KeyProvider(ABC):
    """Wraps and unwraps data keys. Swap the env implementation for KMS/Vault in production."""

    @property
    @abstractmethod
    def current_version(self) -> int: ...

    @abstractmethod
    def wrap(self, dek: bytes, aad: bytes) -> tuple[bytes, int]:
        """Return (wrapped key, master key version used)."""

    @abstractmethod
    def unwrap(self, wrapped: bytes, master_version: int, aad: bytes) -> bytes: ...


class EnvKeyProvider(KeyProvider):
    """Master keys from ``RS_MASTER_KEYS`` (``"1:<b64>,2:<b64>"``), wrapping with AES-256-GCM."""

    def __init__(self, spec: str, current: int) -> None:
        self._keys: dict[int, bytes] = {}
        for part in filter(None, (p.strip() for p in spec.split(","))):
            version_s, _, b64 = part.partition(":")
            key = base64.b64decode(b64, validate=True)
            if len(key) != KEY_BYTES:
                raise ValueError("each master key must be 32 bytes")
            self._keys[int(version_s)] = key
        if current not in self._keys:
            raise ValueError("RS_MASTER_KEY_CURRENT does not match any configured master key")
        self._current = current

    @property
    def current_version(self) -> int:
        return self._current

    def wrap(self, dek: bytes, aad: bytes) -> tuple[bytes, int]:
        nonce = os.urandom(NONCE_BYTES)
        ct = AESGCM(self._keys[self._current]).encrypt(nonce, dek, b"rs-wrap|" + aad)
        return nonce + ct, self._current

    def unwrap(self, wrapped: bytes, master_version: int, aad: bytes) -> bytes:
        key = self._keys.get(master_version)
        if key is None:
            raise CryptoError("unknown master key version")
        try:
            return AESGCM(key).decrypt(
                wrapped[:NONCE_BYTES], wrapped[NONCE_BYTES:], b"rs-wrap|" + aad
            )
        except InvalidTag as exc:
            raise CryptoError("key unwrap failed") from exc


def generate_key() -> bytes:
    return os.urandom(KEY_BYTES)


def wrap_aad(tenant_id: uuid.UUID, purpose: str, version: int) -> bytes:
    return f"{tenant_id}|{purpose}|{version}".encode()


# --------------------------------------------------------------------------- tenant keyring


@dataclass(frozen=True)
class TenantKeyring:
    """Unwrapped keys of one tenant, held in memory only for the duration of a request."""

    tenant_id: uuid.UUID
    data_keys: dict[int, bytes]
    active_data_version: int
    index_key: bytes

    def data_key(self, version: int) -> bytes:
        key = self.data_keys.get(version)
        if key is None:
            raise CryptoError("unknown data key version")
        return key


# --------------------------------------------------------------------------- field encryption


def _field_aad(tenant_id: uuid.UUID, field: str) -> bytes:
    return b"rs-field|" + str(tenant_id).encode() + b"|" + field.encode()


def encrypt_field(keyring: TenantKeyring, field: str, plaintext: str) -> bytes:
    version = keyring.active_data_version
    nonce = os.urandom(NONCE_BYTES)
    ct = AESGCM(keyring.data_key(version)).encrypt(
        nonce, plaintext.encode(), _field_aad(keyring.tenant_id, field)
    )
    return FIELD_MAGIC + struct.pack(">I", version) + nonce + ct


def field_key_version(blob: bytes) -> int:
    if len(blob) < 6 or blob[:2] != FIELD_MAGIC:
        raise CryptoError("bad ciphertext")
    return int(struct.unpack(">I", blob[2:6])[0])


def decrypt_field(keyring: TenantKeyring, field: str, blob: bytes) -> str:
    version = field_key_version(blob)
    nonce, ct = blob[6 : 6 + NONCE_BYTES], blob[6 + NONCE_BYTES :]
    try:
        pt = AESGCM(keyring.data_key(version)).decrypt(
            nonce, ct, _field_aad(keyring.tenant_id, field)
        )
    except InvalidTag as exc:
        raise CryptoError("decryption failed") from exc
    return pt.decode()


def normalize_plate(plate: str) -> str:
    return "".join(ch for ch in plate.upper() if ch.isalnum())


def blind_index(keyring: TenantKeyring, field: str, value: str) -> bytes:
    """Keyed HMAC-SHA256 for exact-match search without storing plaintext."""
    msg = field.encode() + b"|" + value.encode()
    return hmac.new(keyring.index_key, msg, hashlib.sha256).digest()


def mask_plate(plate: str) -> str:
    norm = normalize_plate(plate)
    if len(norm) <= 2:
        return "*" * len(norm)
    return norm[:1] + "*" * (len(norm) - 2) + norm[-1:]


# --------------------------------------------------------------------------- file encryption


def _file_key(dek: bytes, salt: bytes, tenant_id: uuid.UUID, evidence_id: uuid.UUID) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=KEY_BYTES,
        salt=salt,
        info=f"rs-evidence|{tenant_id}|{evidence_id}".encode(),
    ).derive(dek)


def _chunk_nonce(index: int) -> bytes:
    return b"\x00\x00\x00\x00" + struct.pack(">Q", index)


def _chunk_aad(header: bytes, index: int, final: bool) -> bytes:
    return header + struct.pack(">Q?", index, final)


def encrypt_stream(
    keyring: TenantKeyring,
    evidence_id: uuid.UUID,
    src: BinaryIO,
    dst: BinaryIO,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> int:
    """Encrypt ``src`` into ``dst``. Returns plaintext size. Reads one chunk ahead so the last
    chunk can be flagged as final."""
    version = keyring.active_data_version
    salt = os.urandom(FILE_SALT_BYTES)
    header = FILE_MAGIC + struct.pack(">I", version) + salt + struct.pack(">I", chunk_size)
    aead = AESGCM(_file_key(keyring.data_key(version), salt, keyring.tenant_id, evidence_id))
    dst.write(header)
    total, index = 0, 0
    current = src.read(chunk_size)
    while True:
        nxt = src.read(chunk_size)
        final = not nxt
        dst.write(aead.encrypt(_chunk_nonce(index), current, _chunk_aad(header, index, final)))
        total += len(current)
        if final:
            return total
        current, index = nxt, index + 1


def file_key_version(src: BinaryIO) -> int:
    pos = src.tell()
    head = src.read(8)
    src.seek(pos)
    if len(head) < 8 or head[:4] != FILE_MAGIC:
        raise CryptoError("bad evidence file")
    return int(struct.unpack(">I", head[4:8])[0])


def decrypt_stream(
    keyring: TenantKeyring, evidence_id: uuid.UUID, src: BinaryIO
) -> Iterator[bytes]:
    """Yield plaintext chunks. Raises CryptoError on tampering, reordering or truncation."""
    header = src.read(4 + 4 + FILE_SALT_BYTES + 4)
    if len(header) != 44 or header[:4] != FILE_MAGIC:
        raise CryptoError("bad evidence file")
    version = struct.unpack(">I", header[4:8])[0]
    salt = header[8:40]
    chunk_size = struct.unpack(">I", header[40:44])[0]
    if not 0 < chunk_size <= 16 * 1024 * 1024:
        raise CryptoError("bad evidence file")
    aead = AESGCM(_file_key(keyring.data_key(version), salt, keyring.tenant_id, evidence_id))
    index = 0
    current = src.read(chunk_size + TAG_BYTES)
    while True:
        nxt = src.read(chunk_size + TAG_BYTES)
        final = not nxt
        try:
            yield aead.decrypt(_chunk_nonce(index), current, _chunk_aad(header, index, final))
        except InvalidTag as exc:
            raise CryptoError("evidence decryption failed") from exc
        if final:
            return
        current, index = nxt, index + 1


# --------------------------------------------------------------------------- signed URLs


def sign_url_params(key: bytes, purpose: str, resource_id: str, user_id: str, exp: int) -> str:
    msg = f"{purpose}|{resource_id}|{user_id}|{exp}".encode()
    return (
        base64.urlsafe_b64encode(hmac.new(key, msg, hashlib.sha256).digest()).decode().rstrip("=")
    )


def verify_url_params(
    key: bytes, purpose: str, resource_id: str, user_id: str, exp: int, sig: str
) -> bool:
    if exp < int(time.time()):
        return False
    expected = sign_url_params(key, purpose, resource_id, user_id, exp)
    return hmac.compare_digest(expected.encode(), sig.encode())


# --------------------------------------------------------------------------- hashing helpers


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def token_hash(token: str) -> str:
    """Hash for high-entropy random tokens (refresh, invitation). Slow hashing is unnecessary
    for 256-bit random values; SHA-256 prevents use of a leaked DB copy."""
    return hashlib.sha256(token.encode()).hexdigest()
