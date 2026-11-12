"""Encrypted evidence storage. Files are AES-256-GCM ciphertext, keyed per tenant; they are
never served statically and the API decrypts them on the fly for holders of a valid signed URL.

Where the ciphertext lives:
* default: ``<evidence_dir>/<tenant_id>/<evidence_id>.<variant>.enc`` on local disk;
* with ``RS_EVIDENCE_S3_BUCKET``: an S3-compatible bucket, under the same relative key. The
  bucket only ever sees ciphertext; keys and decryption stay in the API process.
"""

from __future__ import annotations

import hashlib
import io
import os
import tempfile
import uuid
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.crypto import TenantKeyring, decrypt_stream, encrypt_stream
from app.models import Alert, Camera, Evidence

VARIANTS = ("redacted", "original")


@lru_cache
def _s3_client() -> Any:
    import boto3

    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.evidence_s3_endpoint,
        region_name=s.evidence_s3_region,
        aws_access_key_id=(
            s.evidence_s3_access_key_id.get_secret_value() if s.evidence_s3_access_key_id else None
        ),
        aws_secret_access_key=(
            s.evidence_s3_secret_access_key.get_secret_value()
            if s.evidence_s3_secret_access_key
            else None
        ),
    )


def _bucket() -> str | None:
    return get_settings().evidence_s3_bucket


def _key(tenant_id: uuid.UUID, evidence_id: uuid.UUID, variant: str) -> str:
    return f"{tenant_id}/{evidence_id}.{variant}.enc"


def _write_encrypted(keyring: TenantKeyring, key_id: uuid.UUID, data: bytes, key: str) -> None:
    bucket = _bucket()
    if bucket:
        # Encrypt into a temporary file first: only ciphertext is ever uploaded.
        with tempfile.TemporaryFile() as tmp:
            encrypt_stream(keyring, key_id, io.BytesIO(data), tmp)
            tmp.seek(0)
            _s3_client().upload_fileobj(
                tmp, bucket, key, ExtraArgs={"ContentType": "application/octet-stream"}
            )
        return
    path = _local_path(key)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "wb") as fh:
        encrypt_stream(keyring, key_id, io.BytesIO(data), fh)
        fh.flush()
        os.fsync(fh.fileno())
    tmp_path.replace(path)


def ingest(
    db: Session,
    keyring: TenantKeyring,
    alert: Alert | None,
    *,
    original: bytes | None,
    redacted: bytes,
    content_type: str,
    kind: str = "keyframe",
    camera: Camera | None = None,
    redaction: str = "full",
) -> Evidence:
    """Store both variants encrypted with the tenant's active DEK and record metadata.

    Evidence belongs to an alert (keyframe, clip) or, for annotated recordings, to a camera.
    ``redaction`` records what the redacted variant actually hides ("heads_only" when the
    pipeline blurred only people's heads, so plates are still visible).
    ``original=None`` (or identical bytes) means no distinct original exists: one copy is stored
    and ``has_original`` is false, so unblur/export-original are refused for it."""
    if (alert is None) == (camera is None):
        raise ValueError("evidence needs exactly one owner: an alert or a camera")
    evidence_id = uuid.uuid4()
    has_original = original is not None and original != redacted
    if original is None:
        original = redacted
    original_key = _key(keyring.tenant_id, evidence_id, "original")
    redacted_key = _key(keyring.tenant_id, evidence_id, "redacted")
    # Each variant gets its own HKDF-derived key: bind the variant into the id used for AAD.
    _write_encrypted(keyring, variant_key_id(evidence_id, "original"), original, original_key)
    if not has_original:
        # No distinct original (pipeline sent one file): stored once; both keys point to it.
        redacted_key = original_key
    else:
        _write_encrypted(keyring, variant_key_id(evidence_id, "redacted"), redacted, redacted_key)
    ev = Evidence(
        id=evidence_id,
        tenant_id=keyring.tenant_id,
        alert_id=alert.id if alert else None,
        camera_id=camera.id if camera else None,
        kind=kind,
        redaction=redaction,
        has_original=has_original,
        content_type=content_type,
        original_path=original_key,
        redacted_path=redacted_key,
        size_bytes=len(original),
        sha256=hashlib.sha256(original).hexdigest(),
        key_version=keyring.active_data_version,
    )
    db.add(ev)
    db.flush()
    return ev


def variant_key_id(evidence_id: uuid.UUID, variant: str) -> uuid.UUID:
    """Distinct, deterministic id per variant so swapping the two files is detected."""
    return uuid.uuid5(evidence_id, variant)


def _local_path(rel: str) -> Path:
    root = get_settings().evidence_dir.resolve()
    path = (root / rel).resolve()
    if root not in path.parents:
        raise ValueError("path escapes evidence root")
    return path


def storage_key(evidence: Evidence, variant: str) -> str:
    """Relative key of a variant (same on disk and in the bucket)."""
    if variant not in VARIANTS:
        raise ValueError("bad variant")
    key = evidence.original_path if variant == "original" else evidence.redacted_path
    if key.startswith("/") or ".." in key.split("/"):
        raise ValueError("path escapes evidence root")
    return key


def file_path(evidence: Evidence, variant: str) -> Path:
    """Local path of a variant (disk storage only)."""
    return _local_path(storage_key(evidence, variant))


def open_decrypted(keyring: TenantKeyring, evidence: Evidence, variant: str) -> Iterator[bytes]:
    key = storage_key(evidence, variant)
    # A single stored copy (identical variants) is encrypted with the original variant's key.
    key_variant = "original" if evidence.redacted_path == evidence.original_path else variant
    key_id = variant_key_id(evidence.id, key_variant)
    bucket = _bucket()
    if bucket:
        try:
            body = _s3_client().get_object(Bucket=bucket, Key=key)["Body"]
        except Exception as exc:
            raise FileNotFoundError(key) from exc
        try:
            yield from decrypt_stream(keyring, key_id, body)
        finally:
            body.close()
        return
    with open(_local_path(key), "rb") as fh:
        yield from decrypt_stream(keyring, key_id, fh)


def delete_files(evidence: Evidence) -> int:
    """Delete the stored file(s) of an evidence row (local disk or bucket). Returns files removed.
    Missing files are not an error (a retried purge must be idempotent)."""
    keys = {evidence.redacted_path, evidence.original_path}
    removed = 0
    bucket = _bucket()
    for key in keys:
        if key.startswith("/") or ".." in key.split("/"):
            raise ValueError("path escapes evidence root")
        if bucket:
            _s3_client().delete_object(Bucket=bucket, Key=key)
            removed += 1
        else:
            path = _local_path(key)
            if path.exists():
                path.unlink()
                removed += 1
    return removed


class EvidencePurgedError(FileNotFoundError):
    """Evidence ciphertext was deliberately removed while metadata remains."""

class StorageUnavailableError(OSError):
    """Evidence storage cannot currently answer the request."""

def has_distinct_original(evidence: Evidence) -> bool:
    return evidence.original_path != evidence.redacted_path

def storage_key(evidence: Evidence, variant: str) -> str:
    return evidence.original_path if variant == "original" else evidence.redacted_path

def object_exists(key: str) -> bool:
    return _local_path(key).is_file()

def storage_state(evidence: Evidence, variant: str = "redacted") -> str:
    if evidence.purged_at is not None: return "purged"
    return "available" if object_exists(storage_key(evidence, variant)) else "missing"

def open_decrypted_key(keyring: TenantKeyring, key_id: uuid.UUID, key: str):
    with open(_local_path(key), "rb") as fh:
        yield from decrypt_stream(keyring, key_id, fh)

def write_encrypted_stream(keyring: TenantKeyring, key_id: uuid.UUID, src, key: str) -> None:
    path=_local_path(key); path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    tmp=path.with_suffix(".tmp")
    try:
        with open(tmp,"wb") as fh: encrypt_stream(keyring,key_id,src,fh); fh.flush(); os.fsync(fh.fileno())
        tmp.replace(path)
    except BaseException:
        tmp.unlink(missing_ok=True); raise

def delete_object(key: str) -> None:
    _local_path(key).unlink(missing_ok=True)

def ensure_duration(db: Session, keyring: TenantKeyring, evidence: Evidence) -> float | None:
    return getattr(evidence, "duration_s", None)


class LegalHoldError(Exception):
    """Evidence is protected by an active legal hold."""

def purge(db: Session, evidence: Evidence, reason: str) -> None:
    from app.models import CaseLegalHold
    from sqlalchemy import select
    if evidence.alert_id is not None and db.scalar(select(CaseLegalHold.id).where(CaseLegalHold.alert_id == evidence.alert_id, CaseLegalHold.released_at.is_(None))):
        raise LegalHoldError(str(evidence.id))
    for variant in ("original", "redacted"):
        delete_object(storage_key(evidence, variant))
    evidence.purged_at = datetime.now(UTC)
    evidence.purge_reason = reason[:200]
    db.flush()
