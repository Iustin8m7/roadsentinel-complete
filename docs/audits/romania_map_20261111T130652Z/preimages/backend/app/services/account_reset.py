"""Account recovery that keeps the security model: no e-mail, no self-service reset.

1. A tenant admin REQUESTS a reset for another user (justification, case reference, fresh MFA).
   It is an approval request of kind ``account_reset``: a different tenant admin approves it.
2. After approval the REQUESTER issues a single-use, short-lived token (shown once) and hands it
   to the user out of band. The approver never sees it; the requester cannot issue it unapproved.
3. The user sets a new password with the token; all sessions and refresh tokens are revoked.
   With ``reset_mfa`` (lost authenticator) TOTP and recovery codes are removed, so the next login
   must enroll again. MFA stays mandatory throughout.
Break-glass without a second admin: ``python -m app.cli reset-account``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import audit
from app.core.audit import AuditAction
from app.core.crypto import token_hash
from app.core.security import hash_password, password_policy_errors, random_token
from app.models import (
    ApprovalKind,
    ApprovalRequest,
    ApprovalStatus,
    Invitation,
    RecoveryCode,
    Role,
    User,
)
from app.services import auth as auth_service
from app.services.approvals import ApprovalError, create_request
from app.services.auth import AuthError, PolicyError


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class IssuedReset:
    token: str
    invitation: Invitation


def request_reset(
    db: Session,
    *,
    requester: User,
    target: User,
    reset_mfa: bool,
    justification: str,
    case_reference: str,
) -> ApprovalRequest:
    if target.id == requester.id:
        raise ApprovalError("Use the password change endpoint for your own account", 400)
    if target.role == Role.system_admin:
        raise ApprovalError("System admin accounts are recovered with the CLI by an operator", 400)
    pending = db.scalars(
        select(ApprovalRequest).where(
            ApprovalRequest.kind == ApprovalKind.account_reset,
            ApprovalRequest.resource_id == target.id,
            ApprovalRequest.status == ApprovalStatus.pending,
        )
    ).first()
    if pending is not None:
        raise ApprovalError("A reset request for this account is already pending", 409)
    req = create_request(
        db,
        tenant_id=requester.tenant_id,
        kind=ApprovalKind.account_reset,
        resource_type="users",
        resource_id=target.id,
        requester_id=requester.id,
        justification=justification,
        case_reference=case_reference,
    )
    req.params = {"reset_mfa": bool(reset_mfa)}
    db.flush()
    return req


def issue_token(db: Session, *, requester_id: uuid.UUID, approval_id: uuid.UUID) -> IssuedReset:
    req = db.get(ApprovalRequest, approval_id, with_for_update=True)
    if req is None or req.kind != ApprovalKind.account_reset or req.requester_id != requester_id:
        raise ApprovalError("Not found", 404)
    params = dict(req.params or {})
    if params.get("issued_at"):
        raise ApprovalError("A token was already issued for this request", 409)
    if (
        req.status != ApprovalStatus.approved
        or req.grant_expires_at is None
        or req.grant_expires_at <= _now()
    ):
        raise ApprovalError("The request is not approved (or the approval expired)", 403)
    target = db.get(User, req.resource_id)
    if target is None or not target.is_active:
        raise ApprovalError("The account is not available", 409)
    token = random_token(32)
    inv = Invitation(
        tenant_id=req.tenant_id,
        email=target.email,
        role=target.role,
        token_hash=token_hash(token),
        invited_by=requester_id,
        kind="reset",
        user_id=target.id,
        reset_mfa=bool(params.get("reset_mfa")),
        expires_at=_now() + timedelta(seconds=get_settings().reset_token_ttl_seconds),
    )
    db.add(inv)
    req.params = {**params, "issued_at": _now().isoformat()}
    req.grant_expires_at = _now()  # the approval is consumed
    db.flush()
    return IssuedReset(token, inv)


def inspect_reset(db: Session, token: str) -> tuple[Invitation, User]:
    inv = auth_service._find_invitation(db, token, "reset")
    user = db.get(User, inv.user_id) if inv.user_id else None
    if user is None or not user.is_active:
        raise AuthError("Invalid or expired invitation")
    return inv, user


def accept_reset(db: Session, token: str, new_password: str) -> User:
    inv, user = inspect_reset(db, token)
    errors = password_policy_errors(new_password, email=user.email)
    if errors:
        raise PolicyError(errors)
    user.password_hash = hash_password(new_password)
    user.failed_login_count = 0
    user.locked_until = None
    if inv.reset_mfa:
        user.mfa_enabled = False
        user.totp_secret_enc = None
        db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
    inv.used_at = _now()
    db.commit()
    revoked = auth_service.revoke_all_sessions(db, user, actor_id=user.id, reason="account_reset")
    audit.record(
        user.tenant_id,
        AuditAction.account_reset_completed,
        actor_id=user.id,
        resource_type="users",
        resource_id=user.id,
        details={"reset_mfa": inv.reset_mfa, "sessions_revoked": revoked},
    )
    return user
