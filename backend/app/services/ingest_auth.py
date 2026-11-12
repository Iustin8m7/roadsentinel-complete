"""HMAC authentication for the detection pipeline (service-to-service).

Wire format (headers on every request to ``/api/ingest/*``)::

    X-RS-Key-Id      public key identifier
    X-RS-Timestamp   unix seconds (accepted within +-ingest_clock_skew_seconds)
    X-RS-Nonce       8..64 URL-safe characters, single use per key
    X-RS-Signature   base64url(HMAC-SHA256(secret, message)), no padding

    message = METHOD "\\n" PATH?QUERY "\\n" TIMESTAMP "\\n" NONCE "\\n" hex(SHA-256(body))

The tenant is derived *only* from the key. Nothing in the URL, headers or body can select it.
Every failure returns the same generic 401, so a caller learns nothing about which part was
wrong. The secret is stored encrypted with the tenant DEK and shown exactly once.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import audit
from app.core.audit import AuditAction
from app.core.crypto import CryptoError, TenantKeyring, decrypt_field, encrypt_field
from app.db import set_tenant
from app.models import IngestNonce, ServiceAccount, ServiceKey
from app.services.keys import load_keyring

H_KEY, H_TS, H_NONCE, H_SIG = "x-rs-key-id", "x-rs-timestamp", "x-rs-nonce", "x-rs-signature"
KEY_ID_RE = re.compile(r"^rsk_[A-Za-z0-9_-]{8,32}$")
NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
SIG_RE = re.compile(r"^[A-Za-z0-9_-]{40,50}$")
SECRET_FIELD = "service_keys.secret"  # noqa: S105 - AAD label, not a credential
MAX_LIVE_KEYS = 2


class IngestAuthError(Exception):
    """Authentication failed. ``reason`` is for the audit log only, never sent to the client."""

    def __init__(self, reason: str, *, rate_limited: bool = False, retry_after: int = 1) -> None:
        super().__init__(reason)
        self.reason = reason
        self.rate_limited = rate_limited
        self.retry_after = retry_after


def body_sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def signing_message(method: str, target: str, timestamp: str, nonce: str, body: bytes) -> bytes:
    return "\n".join([method.upper(), target, timestamp, nonce, body_sha256(body)]).encode()


def sign(secret: str, message: bytes) -> str:
    digest = hmac.new(secret.encode(), message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


# --------------------------------------------------------------------------- key lifecycle


@dataclass
class IssuedKey:
    key_id: str
    secret: str  # shown once, never retrievable afterwards


def create_account(
    db: Session,
    tenant_id: uuid.UUID,
    name: str,
    *,
    camera_ids: list[uuid.UUID] | None = None,
    created_by: uuid.UUID | None = None,
) -> ServiceAccount:
    account = ServiceAccount(
        tenant_id=tenant_id, name=name, camera_ids=camera_ids, created_by=created_by
    )
    db.add(account)
    db.flush()
    return account


def _live(key: ServiceKey, now: datetime) -> bool:
    return key.revoked_at is None and (key.expires_at is None or key.expires_at > now)


def issue_key(
    db: Session,
    keyring: TenantKeyring,
    account: ServiceAccount,
    *,
    overlap_seconds: int | None = None,
) -> IssuedKey:
    """Create a key. Existing live keys keep working for ``overlap_seconds`` (rotation) and
    then expire. At most MAX_LIVE_KEYS live keys per account, so a leaked old key cannot be
    kept alive by repeated issuing."""
    now = datetime.now(UTC)
    overlap = (
        get_settings().ingest_key_overlap_seconds if overlap_seconds is None else overlap_seconds
    )
    keys = db.scalars(select(ServiceKey).where(ServiceKey.account_id == account.id)).all()
    live = [k for k in keys if _live(k, now)]
    if len(live) >= MAX_LIVE_KEYS:
        raise ValueError("too many live keys; revoke one first")
    for k in live:
        if k.expires_at is None or k.expires_at > now + timedelta(seconds=overlap):
            k.expires_at = now + timedelta(seconds=overlap)
    key_id = "rsk_" + secrets.token_urlsafe(12)
    secret = secrets.token_urlsafe(32)
    db.add(
        ServiceKey(
            tenant_id=account.tenant_id,
            account_id=account.id,
            key_id=key_id,
            secret_enc=encrypt_field(keyring, SECRET_FIELD, secret),
        )
    )
    db.flush()
    return IssuedKey(key_id, secret)


def revoke_key(db: Session, account: ServiceAccount, key_id: str) -> bool:
    key = db.scalars(
        select(ServiceKey).where(ServiceKey.account_id == account.id, ServiceKey.key_id == key_id)
    ).first()
    if key is None:
        return False
    if key.revoked_at is None:
        key.revoked_at = datetime.now(UTC)
        db.flush()
    return True


def purge_expired_nonces(db: Session) -> int:
    result = db.execute(delete(IngestNonce).where(IngestNonce.expires_at < datetime.now(UTC)))
    return int(getattr(result, "rowcount", 0) or 0)


# --------------------------------------------------------------------------- verification


@dataclass
class ServicePrincipal:
    """An authenticated pipeline instance. It can create data for its tenant and nothing else."""

    account: ServiceAccount
    key: ServiceKey
    db: Session = field(repr=False)
    _keyring: TenantKeyring | None = field(default=None, repr=False)

    @property
    def tenant_id(self) -> uuid.UUID:
        return self.account.tenant_id

    @property
    def keyring(self) -> TenantKeyring:
        if self._keyring is None:
            self._keyring = load_keyring(self.db, self.tenant_id)
        return self._keyring

    def allows_camera(self, camera_id: uuid.UUID) -> bool:
        scope = self.account.camera_ids
        return scope is None or camera_id in scope

    def audit(self, action: AuditAction | str, **kwargs: object) -> None:
        details = dict(kwargs.pop("details", None) or {})  # type: ignore[call-overload]
        details.update(service_account=self.account.name, key_id=self.key.key_id)
        audit.record(self.tenant_id, action, details=details, **kwargs)  # type: ignore[arg-type]


def _record_failure(tenant_id: uuid.UUID | None, key_id: str | None, reason: str) -> None:
    # Only failures that can be tied to a tenant (a real key id) are written to a chain;
    # unknown keys are rate limited per IP and logged, so strangers cannot grow the audit log.
    if tenant_id is not None:
        audit.record(
            tenant_id,
            AuditAction.ingest_auth_failure,
            details={"key_id": key_id, "reason": reason},
        )


def authenticate(
    db: Session,
    *,
    method: str,
    target: str,
    headers: dict[str, str],
    body: bytes,
    client_ip: str | None = None,
    now: datetime | None = None,
) -> ServicePrincipal:
    """Verify a signed request. Raises IngestAuthError; never reveals which check failed."""
    from app.core.rate_limit import Limit, get_rate_limiter, ip_key

    settings = get_settings()
    now = now or datetime.now(UTC)
    key_id = headers.get(H_KEY, "")
    timestamp = headers.get(H_TS, "")
    nonce = headers.get(H_NONCE, "")
    signature = headers.get(H_SIG, "")
    limiter = get_rate_limiter()

    def fail(reason: str, tenant_id: uuid.UUID | None = None) -> IngestAuthError:
        ok, retry = limiter.hit(ip_key("ingest-fail", client_ip), Limit(30, 300))
        _record_failure(tenant_id, key_id[:40] or None, reason)
        return IngestAuthError(reason, rate_limited=not ok, retry_after=retry)

    if not (KEY_ID_RE.match(key_id) and NONCE_RE.match(nonce) and SIG_RE.match(signature)):
        raise fail("malformed_headers")
    if not (timestamp.isdigit() and len(timestamp) <= 12):
        raise fail("malformed_timestamp")

    tenant_id = db.execute(text("SELECT rs_service_key_tenant(:k)"), {"k": key_id}).scalar()
    if not isinstance(tenant_id, uuid.UUID):
        raise fail("unknown_key")
    set_tenant(db, tenant_id)  # from the key, nowhere else

    key = db.scalars(select(ServiceKey).where(ServiceKey.key_id == key_id)).first()
    account = db.get(ServiceAccount, key.account_id) if key else None
    if key is None or account is None:
        raise fail("unknown_key", tenant_id)
    if key.revoked_at is not None or (key.expires_at is not None and key.expires_at <= now):
        raise fail("key_inactive", tenant_id)
    if not account.is_active:
        raise fail("account_inactive", tenant_id)

    skew = settings.ingest_clock_skew_seconds
    if abs(now.timestamp() - int(timestamp)) > skew:
        raise fail("timestamp_out_of_range", tenant_id)

    try:
        secret = decrypt_field(load_keyring(db, tenant_id), SECRET_FIELD, key.secret_enc)
    except CryptoError as exc:
        raise fail("secret_unreadable", tenant_id) from exc
    expected = sign(secret, signing_message(method, target, timestamp, nonce, body))
    if not hmac.compare_digest(expected, signature):
        raise fail("bad_signature", tenant_id)

    # Only a correctly signed request may consume a nonce, so an attacker cannot burn nonces.
    db.add(
        IngestNonce(
            key_id=key_id,
            nonce=nonce,
            tenant_id=tenant_id,
            expires_at=datetime.fromtimestamp(int(timestamp), UTC) + timedelta(seconds=2 * skew),
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        set_tenant(db, tenant_id)
        audit.record(
            tenant_id,
            AuditAction.ingest_replay,
            details={"key_id": key_id, "account": account.name},
        )
        raise IngestAuthError("replay") from exc

    ok, retry = limiter.hit(f"ingest:key:{key_id}", Limit(settings.ingest_requests_per_minute, 60))
    if not ok:
        audit.record(
            tenant_id,
            AuditAction.ingest_rate_limited,
            details={"key_id": key_id, "account": account.name},
        )
        raise IngestAuthError("rate_limited", rate_limited=True, retry_after=retry)

    key.last_used_at = now
    db.commit()
    return ServicePrincipal(account=account, key=key, db=db)
