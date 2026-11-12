"""Signed audit-chain checkpoints and an append-only local development anchor.

The file adapter is useful for local verification and defines the interface an independently
administered immutable store can implement. A file and private key on the same host are NOT an
independent production anchor; production must store checkpoints/key custody separately.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


class AnchorError(ValueError):
    pass


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


@dataclass(frozen=True)
class Checkpoint:
    tenant_id: str
    sequence: int
    head_hash: str
    created_at: str
    signature: str
    algorithm: str = "Ed25519"

    def signed_fields(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "created_at": self.created_at,
            "head_hash": self.head_hash,
            "sequence": self.sequence,
            "tenant_id": self.tenant_id,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self.signed_fields(), "signature": self.signature}


class LocalFileAnchor:
    """Append signed checkpoints to JSONL and refuse same/older sequence rewrites."""

    def __init__(self, anchor_file: str | Path, private_key_file: str | Path) -> None:
        self.anchor_file = Path(anchor_file)
        self.private_key_file = Path(private_key_file)
        self.public_key_file = self.private_key_file.with_suffix(
            self.private_key_file.suffix + ".pub"
        )

    def _private_key(self, *, create: bool) -> Ed25519PrivateKey:
        self.private_key_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            fd = os.open(self.private_key_file, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        except FileNotFoundError:
            if not create:
                raise AnchorError("signing key is missing") from None
            key = Ed25519PrivateKey.generate()
            raw = key.private_bytes(
                serialization.Encoding.Raw,
                serialization.PrivateFormat.Raw,
                serialization.NoEncryption(),
            )
            try:
                fd = os.open(
                    self.private_key_file,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                    0o600,
                )
                with os.fdopen(fd, "wb") as fh:
                    fh.write(raw)
                    fh.flush()
                    os.fsync(fh.fileno())
            except FileExistsError:
                return self._private_key(create=False)
            public = key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
            _write_exclusive(self.public_key_file, public, 0o644)
            return key
        else:
            if stat.S_IMODE(os.fstat(fd).st_mode) & 0o077:
                os.close(fd)
                raise AnchorError("signing key permissions must be 0600 or stricter")
            with os.fdopen(fd, "rb") as fh:
                raw = fh.read(33)
            if len(raw) != 32:
                raise AnchorError("signing key file is malformed")
            key = Ed25519PrivateKey.from_private_bytes(raw)
            public = key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
            if not self.public_key_file.exists():
                _write_exclusive(self.public_key_file, public, 0o644)
            elif self.public_key_file.read_bytes() != public:
                raise AnchorError("public key does not match signing key")
            return key

    def publish(self, tenant_id: uuid.UUID, sequence: int, head_hash: str) -> Checkpoint:
        if (
            sequence < 0
            or len(head_hash) != 64
            or any(c not in "0123456789abcdef" for c in head_hash)
        ):
            raise AnchorError("invalid audit checkpoint")
        tenant = str(tenant_id)
        previous = [item for item in self.read_all() if item.tenant_id == tenant]
        if previous:
            last = previous[-1]
            if sequence < last.sequence or (
                sequence == last.sequence and head_hash != last.head_hash
            ):
                raise AnchorError(
                    "checkpoint sequence is older or conflicts with the anchored head"
                )
            if sequence == last.sequence:
                return last
        fields = {
            "algorithm": "Ed25519",
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "head_hash": head_hash,
            "sequence": sequence,
            "tenant_id": tenant,
        }
        signature = (
            base64.urlsafe_b64encode(self._private_key(create=True).sign(_canonical(fields)))
            .decode()
            .rstrip("=")
        )
        checkpoint = Checkpoint(**fields, signature=signature)
        self.anchor_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        line = (
            json.dumps(checkpoint.as_dict(), sort_keys=True, separators=(",", ":")).encode() + b"\n"
        )
        fd = os.open(
            self.anchor_file,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        with os.fdopen(fd, "ab") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        return checkpoint

    def read_all(self) -> list[Checkpoint]:
        if not self.anchor_file.exists():
            return []
        try:
            lines = self.anchor_file.read_text(encoding="utf-8").splitlines()
            items = [Checkpoint(**json.loads(line)) for line in lines if line]
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as exc:
            raise AnchorError("anchor file is malformed") from exc
        latest: dict[str, Checkpoint] = {}
        for item in items:
            _verify_one(item, self.public_key_file.read_bytes())
            prior = latest.get(item.tenant_id)
            if prior and item.sequence <= prior.sequence:
                raise AnchorError("anchor sequence is not strictly increasing")
            latest[item.tenant_id] = item
        return items

    def latest(self, tenant_id: uuid.UUID) -> Checkpoint | None:
        return next(
            (item for item in reversed(self.read_all()) if item.tenant_id == str(tenant_id)), None
        )


def _write_exclusive(path: Path, data: bytes, mode: int) -> None:
    try:
        fd = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode
        )
    except FileExistsError:
        if path.read_bytes() != data:
            raise AnchorError("existing public key differs from signing key") from None
        return
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())


def _verify_one(checkpoint: Checkpoint, public_bytes: bytes) -> None:
    if (
        checkpoint.algorithm != "Ed25519"
        or len(checkpoint.head_hash) != 64
        or checkpoint.sequence < 0
    ):
        raise AnchorError("checkpoint fields are invalid")
    try:
        signature = base64.urlsafe_b64decode(
            checkpoint.signature + "=" * (-len(checkpoint.signature) % 4)
        )
        Ed25519PublicKey.from_public_bytes(public_bytes).verify(
            signature, _canonical(checkpoint.signed_fields())
        )
    except (ValueError, InvalidSignature) as exc:
        raise AnchorError("checkpoint signature is invalid") from exc


def verify_anchor_file(anchor_file: str | Path, public_key_file: str | Path) -> list[Checkpoint]:
    """Verify signatures and monotonic per-tenant sequence using a separately held public key."""
    public = Path(public_key_file).read_bytes()
    items: list[Checkpoint] = []
    latest: dict[str, int] = {}
    try:
        for line in Path(anchor_file).read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            item = Checkpoint(**json.loads(line))
            _verify_one(item, public)
            if item.sequence <= latest.get(item.tenant_id, -1):
                raise AnchorError("anchor sequence is not strictly increasing")
            latest[item.tenant_id] = item.sequence
            items.append(item)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as exc:
        raise AnchorError("anchor file is missing or malformed") from exc
    return items


def public_key_fingerprint(public_key_file: str | Path) -> str:
    return hashlib.sha256(Path(public_key_file).read_bytes()).hexdigest()
