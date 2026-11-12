"""Private, tenant-encrypted media storage for recorded-video analysis."""

from __future__ import annotations

import os
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings
from app.core.crypto import (
    FILE_MAGIC,
    TAG_BYTES,
    CryptoError,
    TenantKeyring,
    _chunk_aad,
    _chunk_nonce,
    _file_key,
    decrypt_stream,
    encrypt_stream,
)

MAX_PLAINTEXT_BYTES = 1024 * 1024 * 1024


def _root() -> Path:
    requested = get_settings().evidence_dir / "offline-analysis"
    requested.mkdir(mode=0o700, parents=True, exist_ok=True)
    if requested.is_symlink():
        raise ValueError("offline media storage must not be a symlink")
    root = requested.resolve()
    os.chmod(root, 0o700)
    return root


def storage_path(key: str) -> Path:
    if not key.startswith("offline-analysis/") or ".." in key.split("/") or key.startswith("/"):
        raise ValueError("invalid private media storage key")
    path = (get_settings().evidence_dir.resolve() / key).resolve()
    root = _root()
    if root not in path.parents:
        raise ValueError("private media path escapes storage root")
    return path


def storage_key(tenant_id: uuid.UUID, object_id: uuid.UUID, variant: str) -> str:
    if variant not in {"source", "output", "observations"}:
        raise ValueError("invalid media variant")
    return f"offline-analysis/{tenant_id}/{object_id}/{variant}.rse"


def stage_plaintext() -> tuple[BinaryIO, Path]:
    fd, name = tempfile.mkstemp(prefix="upload-", suffix=".part", dir=_root())
    os.fchmod(fd, 0o600)
    return os.fdopen(fd, "wb"), Path(name)


def encrypt_file(keyring: TenantKeyring, encryption_id: uuid.UUID, source: Path, key: str) -> int:
    destination = storage_path(key)
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(destination.parent, 0o700)
    tmp = destination.with_suffix(destination.suffix + f".{uuid.uuid4().hex}.tmp")
    try:
        with source.open("rb") as src, tmp.open("xb") as dst:
            os.chmod(tmp, 0o600)
            size = encrypt_stream(keyring, encryption_id, src, dst)
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(tmp, destination)
        return size
    finally:
        tmp.unlink(missing_ok=True)


@contextmanager
def decrypted_temp(keyring: TenantKeyring, encryption_id: uuid.UUID, key: str) -> Iterator[Path]:
    root = _root()
    with tempfile.TemporaryDirectory(prefix="work-", dir=root) as folder:
        os.chmod(folder, 0o700)
        target = Path(folder) / "media.bin"
        with storage_path(key).open("rb") as src, target.open("xb") as dst:
            os.chmod(target, 0o600)
            for chunk in decrypt_stream(keyring, encryption_id, src):
                dst.write(chunk)
        yield target


def decrypt_range(
    keyring: TenantKeyring,
    encryption_id: uuid.UUID,
    key: str,
    *,
    start: int,
    end: int,
    plaintext_size: int,
) -> Iterator[bytes]:
    """Authenticate and yield only the requested byte range from independently sealed chunks."""
    if start < 0 or end < start or end >= plaintext_size or plaintext_size > MAX_PLAINTEXT_BYTES:
        raise ValueError("invalid media range")
    with storage_path(key).open("rb") as src:
        header = src.read(44)
        if len(header) != 44 or header[:4] != FILE_MAGIC:
            raise CryptoError("bad media ciphertext")
        version = int.from_bytes(header[4:8], "big")
        chunk_size = int.from_bytes(header[40:44], "big")
        if not 0 < chunk_size <= 16 * 1024 * 1024:
            raise CryptoError("bad media ciphertext")
        aead = AESGCM(
            _file_key(keyring.data_key(version), header[8:40], keyring.tenant_id, encryption_id)
        )
        first_chunk, last_chunk = start // chunk_size, end // chunk_size
        for index in range(first_chunk, last_chunk + 1):
            offset = index * chunk_size
            plain_len = min(chunk_size, plaintext_size - offset)
            src.seek(44 + index * (chunk_size + TAG_BYTES))
            cipher = src.read(plain_len + TAG_BYTES)
            if len(cipher) != plain_len + TAG_BYTES:
                raise CryptoError("truncated media ciphertext")
            final = offset + plain_len == plaintext_size
            try:
                plain = aead.decrypt(_chunk_nonce(index), cipher, _chunk_aad(header, index, final))
            except Exception as exc:
                raise CryptoError("media authentication failed") from exc
            lo = max(start, offset) - offset
            hi = min(end + 1, offset + plain_len) - offset
            yield plain[lo:hi]
