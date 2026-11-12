"""Tenant admin management of pipeline identities and their HMAC keys."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.core.audit import AuditAction
from app.core.policy import Permission
from app.deps import Principal, not_found, require, require_fresh_mfa
from app.models import Camera, ServiceAccount, ServiceKey
from app.services import ingest_auth

router = APIRouter(prefix="/api/service-accounts", tags=["service-accounts"])


class KeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key_id: str
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    last_used_at: datetime | None


class AccountOut(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool
    camera_ids: list[uuid.UUID] | None
    keys: list[KeyOut]


class AccountIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    camera_ids: list[uuid.UUID] | None = Field(default=None, max_length=200)


class AccountPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool


class KeyIssued(BaseModel):
    key_id: str
    secret: str  # displayed once


def _out(principal: Principal, account: ServiceAccount) -> AccountOut:
    keys = principal.db.scalars(
        select(ServiceKey)
        .where(ServiceKey.account_id == account.id)
        .order_by(ServiceKey.created_at.desc())
    ).all()
    return AccountOut(
        id=account.id,
        name=account.name,
        is_active=account.is_active,
        camera_ids=account.camera_ids,
        keys=[KeyOut.model_validate(k) for k in keys],
    )


def _account(principal: Principal, account_id: uuid.UUID) -> ServiceAccount:
    account = principal.db.get(ServiceAccount, account_id)
    if account is None:
        not_found(principal, "service_accounts", account_id)
    return account


@router.get("", response_model=list[AccountOut])
def list_accounts(
    principal: Principal = Depends(require(Permission.service_accounts_manage)),
) -> list[AccountOut]:
    accounts = principal.db.scalars(select(ServiceAccount).order_by(ServiceAccount.name)).all()
    return [_out(principal, a) for a in accounts]


@router.post("", response_model=AccountOut, status_code=201)
def create_account(
    body: AccountIn, principal: Principal = Depends(require(Permission.service_accounts_manage))
) -> AccountOut:
    require_fresh_mfa(principal)
    if body.camera_ids:
        found = set(
            principal.db.scalars(select(Camera.id).where(Camera.id.in_(body.camera_ids))).all()
        )
        if found != set(body.camera_ids):  # RLS hides other tenants' cameras
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown camera")
    account = ingest_auth.create_account(
        principal.db,
        principal.tenant_id,
        body.name,
        camera_ids=body.camera_ids,
        created_by=principal.user_id,
    )
    principal.db.commit()
    principal.audit(
        AuditAction.service_account_created,
        resource_type="service_accounts",
        resource_id=account.id,
        details={"name": account.name, "cameras": len(body.camera_ids or [])},
    )
    return _out(principal, account)


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(
    account_id: uuid.UUID,
    body: AccountPatch,
    principal: Principal = Depends(require(Permission.service_accounts_manage)),
) -> AccountOut:
    require_fresh_mfa(principal)
    account = _account(principal, account_id)
    account.is_active = body.is_active
    principal.db.commit()
    principal.audit(
        AuditAction.service_account_updated,
        resource_type="service_accounts",
        resource_id=account.id,
        details={"is_active": body.is_active},
    )
    return _out(principal, account)


@router.post("/{account_id}/keys", response_model=KeyIssued, status_code=201)
def issue_key(
    account_id: uuid.UUID,
    principal: Principal = Depends(require(Permission.service_accounts_manage)),
) -> KeyIssued:
    """Issue (or rotate to) a new key. Older live keys keep working for the overlap window."""
    require_fresh_mfa(principal)
    account = _account(principal, account_id)
    try:
        issued = ingest_auth.issue_key(principal.db, principal.keyring, account)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    principal.db.commit()
    principal.audit(
        AuditAction.service_key_issued,
        resource_type="service_accounts",
        resource_id=account.id,
        details={"key_id": issued.key_id},
    )
    return KeyIssued(key_id=issued.key_id, secret=issued.secret)


@router.delete("/{account_id}/keys/{key_id}", status_code=204)
def revoke_key(
    account_id: uuid.UUID,
    key_id: str,
    principal: Principal = Depends(require(Permission.service_accounts_manage)),
) -> None:
    require_fresh_mfa(principal)
    account = _account(principal, account_id)
    if not ingest_auth.revoke_key(principal.db, account, key_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    principal.db.commit()
    principal.audit(
        AuditAction.service_key_revoked,
        resource_type="service_accounts",
        resource_id=account.id,
        details={"key_id": key_id},
    )
