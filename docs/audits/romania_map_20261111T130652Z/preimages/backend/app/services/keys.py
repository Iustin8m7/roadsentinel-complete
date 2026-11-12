"""Tenant key management: creation, loading (unwrapping) and rotation."""

from __future__ import annotations

import uuid
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.crypto import (
    CryptoError,
    EnvKeyProvider,
    KeyProvider,
    TenantKeyring,
    decrypt_field,
    encrypt_field,
    field_key_version,
    generate_key,
    wrap_aad,
)
from app.models import Alert, ServiceKey, TenantKey, User

DATA, INDEX = "data", "index"


@lru_cache
def get_key_provider() -> KeyProvider:
    s = get_settings()
    return EnvKeyProvider(s.master_keys.get_secret_value(), s.master_key_current)


def _new_key_row(tenant_id: uuid.UUID, purpose: str, version: int) -> TenantKey:
    wrapped, master_version = get_key_provider().wrap(
        generate_key(), wrap_aad(tenant_id, purpose, version)
    )
    return TenantKey(
        tenant_id=tenant_id,
        purpose=purpose,
        version=version,
        wrapped_key=wrapped,
        master_key_version=master_version,
        active=True,
    )


def create_tenant_keys(db: Session, tenant_id: uuid.UUID) -> None:
    db.add_all([_new_key_row(tenant_id, DATA, 1), _new_key_row(tenant_id, INDEX, 1)])
    db.flush()


def ensure_tenant_keys(db: Session, tenant_id: uuid.UUID) -> None:
    """Add only missing initial key purposes for a partially initialized tenant."""
    rows = db.scalars(select(TenantKey).where(TenantKey.tenant_id == tenant_id)).all()
    for purpose in (DATA, INDEX):
        purpose_rows = [row for row in rows if row.purpose == purpose]
        if any(row.active for row in purpose_rows):
            continue
        for row in purpose_rows:
            row.active = False
        next_version = max((row.version for row in purpose_rows), default=0) + 1
        db.add(_new_key_row(tenant_id, purpose, next_version))
    db.flush()


def load_keyring(db: Session, tenant_id: uuid.UUID) -> TenantKeyring:
    """Unwrap all key versions of the tenant. RLS guarantees only that tenant's rows return;
    the AAD (tenant, purpose, version) guarantees a row copied from another tenant won't unwrap."""
    provider = get_key_provider()
    rows = db.scalars(select(TenantKey).where(TenantKey.tenant_id == tenant_id)).all()
    data: dict[int, bytes] = {}
    active_version: int | None = None
    index_key: bytes | None = None
    for row in rows:
        key = provider.unwrap(
            row.wrapped_key, row.master_key_version, wrap_aad(tenant_id, row.purpose, row.version)
        )
        if row.purpose == DATA:
            data[row.version] = key
            if row.active and (active_version is None or row.version > active_version):
                active_version = row.version
        elif row.purpose == INDEX and row.active:
            index_key = key
    if active_version is None or index_key is None:
        raise CryptoError("tenant has no active keys")
    return TenantKeyring(tenant_id, data, active_version, index_key)


def rewrap_tenant_keys(db: Session, tenant_id: uuid.UUID) -> int:
    """Re-wrap every key of the tenant under the *current* master key version (used after a
    master key rotation). Plaintext DEKs never change, so no data needs re-encryption."""
    provider = get_key_provider()
    count = 0
    for row in db.scalars(select(TenantKey).where(TenantKey.tenant_id == tenant_id)).all():
        aad = wrap_aad(tenant_id, row.purpose, row.version)
        dek = provider.unwrap(row.wrapped_key, row.master_key_version, aad)
        row.wrapped_key, row.master_key_version = provider.wrap(dek, aad)
        count += 1
    db.flush()
    return count


def rotate_data_key(db: Session, tenant_id: uuid.UUID, *, reencrypt: bool = True) -> int:
    """Create a new DEK version and make it active. Old versions stay for decryption of
    existing ciphertext (evidence files, unconverted fields). With ``reencrypt``, encrypted
    columns are rewritten under the new version. Returns the new version."""
    rows = db.scalars(
        select(TenantKey).where(TenantKey.tenant_id == tenant_id, TenantKey.purpose == DATA)
    ).all()
    new_version = max(r.version for r in rows) + 1
    for r in rows:
        r.active = False
    db.add(_new_key_row(tenant_id, DATA, new_version))
    db.flush()
    if reencrypt:
        reencrypt_fields(db, tenant_id)
    return new_version


def reencrypt_fields(db: Session, tenant_id: uuid.UUID) -> int:
    keyring = load_keyring(db, tenant_id)
    changed = 0
    for alert in db.scalars(select(Alert).where(Alert.plate_enc.is_not(None))).all():
        assert alert.plate_enc is not None
        if field_key_version(alert.plate_enc) != keyring.active_data_version:
            plain = decrypt_field(keyring, "alerts.plate", alert.plate_enc)
            alert.plate_enc = encrypt_field(keyring, "alerts.plate", plain)
            changed += 1
    for user in db.scalars(select(User).where(User.totp_secret_enc.is_not(None))).all():
        assert user.totp_secret_enc is not None
        if field_key_version(user.totp_secret_enc) != keyring.active_data_version:
            plain = decrypt_field(keyring, "users.totp_secret", user.totp_secret_enc)
            user.totp_secret_enc = encrypt_field(keyring, "users.totp_secret", plain)
            changed += 1
    for key in db.scalars(select(ServiceKey)).all():
        if field_key_version(key.secret_enc) != keyring.active_data_version:
            plain = decrypt_field(keyring, "service_keys.secret", key.secret_enc)
            key.secret_enc = encrypt_field(keyring, "service_keys.secret", plain)
            changed += 1
    db.flush()
    return changed
