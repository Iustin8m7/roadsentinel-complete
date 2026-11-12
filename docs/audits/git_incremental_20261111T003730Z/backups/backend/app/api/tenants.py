from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core import audit
from app.core.audit import AuditAction
from app.core.policy import Permission
from app.db import tenant_session
from app.deps import Principal, get_principal, require, require_fresh_mfa
from app.models import Role, Tenant
from app.schemas.users import (
    InvitationCreatedOut,
    InvitationOut,
    KeyRotationOut,
    TenantCreatedOut,
    TenantCreateIn,
    TenantOut,
)
from app.services import auth as auth_service
from app.services.keys import rotate_data_key
from app.services.tenants import create_tenant

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


@router.get("/current", response_model=TenantOut)
def current_tenant(principal: Principal = Depends(get_principal)) -> Tenant:
    tenant = principal.db.get(Tenant, principal.tenant_id)
    assert tenant is not None
    return tenant


@router.post("", response_model=TenantCreatedOut, status_code=201)
def create(
    body: TenantCreateIn, principal: Principal = Depends(require(Permission.tenants_create))
) -> TenantCreatedOut:
    """System admin creates a police unit and an invitation for its first tenant admin."""
    require_fresh_mfa(principal)
    exists = principal.db.execute(
        text("SELECT 1 FROM rs_auth_find_user(:e)"), {"e": body.admin_email}
    ).first()
    if exists:
        raise HTTPException(409, "Admin e-mail already registered")
    try:
        tenant_id = create_tenant(body.name, body.slug)
    except IntegrityError as exc:
        raise HTTPException(409, "Slug already in use") from exc
    with tenant_session(tenant_id) as db:
        created = auth_service.create_invitation(
            db, tenant_id, body.admin_email, Role.tenant_admin, None
        )
        db.commit()
        tenant = db.get(Tenant, tenant_id)
        assert tenant is not None
        tenant_out = TenantOut.model_validate(tenant)
        inv_out = InvitationOut.model_validate(created.invitation)
        audit.append(
            db,
            tenant_id,
            AuditAction.tenant_created,
            actor_id=principal.user_id,
            details={"created_by_tenant_id": str(principal.tenant_id)},
        )
        db.commit()
    principal.audit(AuditAction.tenant_created, resource_type="tenants", resource_id=tenant_id)
    return TenantCreatedOut(
        tenant=tenant_out,
        admin_invitation=InvitationCreatedOut(
            **inv_out.model_dump(), token=created.token, accept_path=f"/invite#{created.token}"
        ),
    )


@router.post("/current/rotate-key", response_model=KeyRotationOut)
def rotate_key(principal: Principal = Depends(require(Permission.keys_rotate))) -> KeyRotationOut:
    require_fresh_mfa(principal)
    from app.services.keys import reencrypt_fields

    version = rotate_data_key(principal.db, principal.tenant_id, reencrypt=False)
    changed = reencrypt_fields(principal.db, principal.tenant_id)
    principal.db.commit()
    principal.audit(
        AuditAction.key_rotated,
        resource_type="tenants",
        resource_id=principal.tenant_id,
        details={"new_version": version, "reencrypted_fields": changed},
    )
    return KeyRotationOut(new_data_key_version=version, reencrypted_fields=changed)
