from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.sessions import to_out
from app.core.audit import AuditAction
from app.core.policy import TENANT_ASSIGNABLE_ROLES, Permission
from app.deps import Principal, not_found, require, require_fresh_mfa
from app.models import Invitation, Role, User, UserSession
from app.schemas.approvals import ApprovalOut
from app.schemas.auth import SessionOut
from app.schemas.users import (
    InvitationCreatedOut,
    InvitationIn,
    InvitationOut,
    ResetIssuedOut,
    ResetRequestIn,
    UserOut,
    UserUpdateIn,
)
from app.services import account_reset
from app.services import auth as auth_service
from app.services.approvals import ApprovalError, is_grant_active

router = APIRouter(prefix="/api/users", tags=["users"])

manage = require(Permission.users_manage)


def _assignable(principal: Principal) -> frozenset[Role]:
    if principal.role == Role.system_admin:
        return frozenset({Role.system_admin})
    return TENANT_ASSIGNABLE_ROLES


def _get_user(principal: Principal, user_id: uuid.UUID) -> User:
    user = principal.db.get(User, user_id)
    if user is None:
        not_found(principal, "users", user_id)
    return user


@router.get("", response_model=list[UserOut])
def list_users(principal: Principal = Depends(manage)) -> list[User]:
    return list(principal.db.scalars(select(User).order_by(User.email)).all())


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID, body: UserUpdateIn, principal: Principal = Depends(manage)
) -> User:
    require_fresh_mfa(principal)
    user = _get_user(principal, user_id)
    if user.id == principal.user_id:
        raise HTTPException(400, "You cannot change your own role or status")
    changes: dict[str, object] = {}
    if body.role is not None and body.role != user.role:
        if body.role not in _assignable(principal):
            raise HTTPException(403, "Forbidden")
        changes["role"] = {"from": user.role.value, "to": body.role.value}
        user.role = body.role
    if body.is_active is not None and body.is_active != user.is_active:
        changes["is_active"] = body.is_active
        user.is_active = body.is_active
    principal.db.commit()
    if body.is_active is False:
        auth_service.revoke_all_sessions(
            principal.db, user, actor_id=principal.user_id, reason="user_disabled"
        )
    if changes:
        principal.audit(
            AuditAction.user_updated, resource_type="users", resource_id=user.id, details=changes
        )
    return user


@router.get("/invitations", response_model=list[InvitationOut])
def list_invitations(principal: Principal = Depends(manage)) -> list[Invitation]:
    return list(
        principal.db.scalars(
            select(Invitation).order_by(Invitation.created_at.desc()).limit(100)
        ).all()
    )


@router.post("/invitations", response_model=InvitationCreatedOut, status_code=201)
def create_invitation(
    body: InvitationIn, principal: Principal = Depends(manage)
) -> InvitationCreatedOut:
    require_fresh_mfa(principal)
    if body.role not in _assignable(principal):
        raise HTTPException(403, "Forbidden")
    created = auth_service.create_invitation(
        principal.db, principal.tenant_id, body.email, body.role, principal.user_id
    )
    principal.db.commit()
    inv = created.invitation
    principal.audit(
        AuditAction.invitation_created,
        resource_type="invitations",
        resource_id=inv.id,
        details={"role": inv.role.value},
    )
    return InvitationCreatedOut(
        **InvitationOut.model_validate(inv).model_dump(),
        token=created.token,
        accept_path=f"/invite#{created.token}",
    )


@router.delete("/invitations/{invitation_id}", status_code=204)
def revoke_invitation(invitation_id: uuid.UUID, principal: Principal = Depends(manage)) -> None:
    require_fresh_mfa(principal)
    inv = principal.db.get(Invitation, invitation_id)
    if inv is None:
        not_found(principal, "invitations", invitation_id)
    if inv.used_at is None and inv.revoked_at is None:
        from datetime import UTC, datetime

        inv.revoked_at = datetime.now(UTC)
        principal.db.commit()
    principal.audit(AuditAction.invitation_revoked, resource_type="invitations", resource_id=inv.id)


@router.get("/{user_id}/sessions", response_model=list[SessionOut])
def list_user_sessions(
    user_id: uuid.UUID, principal: Principal = Depends(require(Permission.sessions_manage_all))
) -> list[SessionOut]:
    user = _get_user(principal, user_id)
    rows = principal.db.scalars(
        select(UserSession)
        .where(UserSession.user_id == user.id)
        .order_by(UserSession.last_seen_at.desc())
    ).all()
    return [to_out(s, principal.session.id) for s in rows]


@router.delete("/{user_id}/sessions/{session_id}", status_code=204)
def revoke_user_session(
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    principal: Principal = Depends(require(Permission.sessions_manage_all)),
) -> None:
    require_fresh_mfa(principal)
    user = _get_user(principal, user_id)
    s = principal.db.get(UserSession, session_id)
    if s is None or s.user_id != user.id:
        not_found(principal, "user_sessions", session_id)
    auth_service.revoke_session(principal.db, s, actor_id=principal.user_id, reason="admin_revoked")


@router.post("/{user_id}/reset-requests", response_model=ApprovalOut, status_code=201)
def request_account_reset(
    user_id: uuid.UUID, body: ResetRequestIn, principal: Principal = Depends(manage)
) -> ApprovalOut:
    """Four-eyes account recovery, step 1; a different tenant admin approves in /api/approvals."""
    require_fresh_mfa(principal)
    target = _get_user(principal, user_id)
    try:
        req = account_reset.request_reset(
            principal.db,
            requester=principal.user,
            target=target,
            reset_mfa=body.reset_mfa,
            justification=body.justification,
            case_reference=body.case_reference,
        )
    except ApprovalError as exc:
        raise HTTPException(exc.status_code, exc.message) from None
    principal.db.commit()
    principal.audit(
        AuditAction.account_reset_requested,
        resource_type="users",
        resource_id=target.id,
        details={"approval_id": str(req.id), "reset_mfa": body.reset_mfa},
    )
    out = ApprovalOut.model_validate(req)
    out.grant_active = is_grant_active(req)
    return out


@router.post("/reset-requests/{approval_id}/issue", response_model=ResetIssuedOut)
def issue_reset_token(
    approval_id: uuid.UUID, principal: Principal = Depends(manage)
) -> ResetIssuedOut:
    """Step 2, by the requester only and only after approval: a single-use, short-lived token."""
    require_fresh_mfa(principal)
    try:
        issued = account_reset.issue_token(
            principal.db, requester_id=principal.user_id, approval_id=approval_id
        )
    except ApprovalError as exc:
        principal.audit(
            AuditAction.access_denied,
            resource_type="approval_requests",
            resource_id=approval_id,
            details={"reason": "reset_issue_refused"},
        )
        raise HTTPException(exc.status_code, exc.message) from None
    principal.db.commit()
    principal.audit(
        AuditAction.account_reset_issued,
        resource_type="users",
        resource_id=issued.invitation.user_id,
        details={
            "approval_id": str(approval_id),
            "expires_at": issued.invitation.expires_at.isoformat(),
        },
    )
    return ResetIssuedOut(
        token=issued.token,
        accept_path=f"/reset#{issued.token}",
        expires_at=issued.invitation.expires_at,
    )


@router.post("/{user_id}/sessions/revoke-all")
def revoke_all_user_sessions(
    user_id: uuid.UUID, principal: Principal = Depends(require(Permission.sessions_manage_all))
) -> dict[str, int]:
    require_fresh_mfa(principal)
    user = _get_user(principal, user_id)
    n = auth_service.revoke_all_sessions(
        principal.db, user, actor_id=principal.user_id, reason="admin_revoked"
    )
    principal.audit(
        AuditAction.sessions_revoked_bulk,
        resource_type="users",
        resource_id=user.id,
        details={"count": n},
    )
    return {"revoked": n}
