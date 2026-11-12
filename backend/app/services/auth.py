"""Authentication flows: password step, MFA (TOTP / recovery codes), enrollment, sessions,
refresh-token rotation with reuse detection, re-authentication and invitations.

Error policy: every credential failure raises ``AuthError`` with the same generic message, so
responses never reveal whether an account exists, is locked, or which factor was wrong.
"""

from __future__ import annotations

import base64
import io
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import qrcode
import qrcode.image.svg
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import audit
from app.core.audit import AuditAction, request_context
from app.core.crypto import decrypt_field, encrypt_field, token_hash
from app.core.rate_limit import (
    INVITE_PER_IP,
    LOGIN_PER_ACCOUNT,
    LOGIN_PER_IP,
    MFA_PER_ACCOUNT,
    MFA_PER_IP,
    REFRESH_PER_IP,
    Limit,
    account_key,
    get_rate_limiter,
    ip_key,
)
from app.core.security import (
    burn_password_check,
    create_access_token,
    generate_recovery_codes,
    hash_password,
    new_totp_secret,
    normalize_recovery_code,
    password_policy_errors,
    random_token,
    totp_uri,
    verify_password,
    verify_totp,
)
from app.db import set_tenant
from app.models import Invitation, RecoveryCode, RefreshToken, Tenant, User, UserSession
from app.services.keys import load_keyring

GENERIC_AUTH_ERROR = "Invalid credentials"
TOTP_FIELD = "users.totp_secret"


class AuthError(Exception):
    def __init__(self, message: str = GENERIC_AUTH_ERROR) -> None:
        super().__init__(message)
        self.message = message


class RateLimited(Exception):  # noqa: N818 - reads better at call sites
    def __init__(self, retry_after: int) -> None:
        super().__init__("rate limited")
        self.retry_after = retry_after


class PolicyError(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass
class IssuedSession:
    session: UserSession
    access_token: str
    refresh_token: str


def _now() -> datetime:
    return datetime.now(UTC)


def _ip() -> str | None:
    ctx = request_context.get()
    return ctx.ip if ctx else None


def _ua() -> str | None:
    ctx = request_context.get()
    return (ctx.user_agent or "")[:400] if ctx and ctx.user_agent else None


def check_rate(*rules: tuple[str, Limit], tenant_id: uuid.UUID | None = None) -> None:
    limiter = get_rate_limiter()
    for key, limit in rules:
        allowed, retry_after = limiter.hit(key, limit)
        if not allowed:
            if tenant_id is not None:
                audit.record(
                    tenant_id, AuditAction.rate_limited, details={"scope": key.split(":")[0]}
                )
            raise RateLimited(retry_after)


def _platform_tenant(db: Session) -> uuid.UUID | None:
    return audit.platform_tenant_id(db)


def _register_failure(db: Session, user: User) -> None:
    s = get_settings()
    user.failed_login_count += 1
    if user.failed_login_count >= s.lockout_threshold:
        user.locked_until = _now() + timedelta(seconds=s.lockout_seconds)
        user.failed_login_count = 0
        db.commit()
        audit.record(
            user.tenant_id,
            AuditAction.login_locked,
            actor_id=user.id,
            resource_type="users",
            resource_id=user.id,
            details={"lockout_seconds": s.lockout_seconds},
        )
    else:
        db.commit()


def _is_locked(user: User) -> bool:
    return user.locked_until is not None and user.locked_until > _now()


# --------------------------------------------------------------------------- password step


@dataclass
class PasswordStepResult:
    user: User
    enrollment_required: bool


def login_password(db: Session, email: str, password: str) -> PasswordStepResult:
    email = email.strip().lower()
    check_rate(
        (ip_key("login", _ip()), LOGIN_PER_IP),
        (account_key("login", email), LOGIN_PER_ACCOUNT),
        tenant_id=None,
    )
    row = db.execute(
        text("SELECT user_id, tenant_id FROM rs_auth_find_user(:e)"), {"e": email}
    ).first()
    if row is None:
        burn_password_check(password)
        platform = _platform_tenant(db)
        if platform:
            audit.record(
                platform,
                AuditAction.login_failure,
                details={"reason": "unknown_account", "email_hash": account_key("x", email)[7:]},
            )
        raise AuthError()

    user_id, tenant_id = row
    set_tenant(db, tenant_id)
    user = db.get(User, user_id)
    assert user is not None
    if not user.is_active or _is_locked(user):
        burn_password_check(password)
        audit.record(
            tenant_id,
            AuditAction.login_failure,
            actor_id=user.id,
            details={"reason": "inactive" if not user.is_active else "locked"},
        )
        raise AuthError()
    if not verify_password(user.password_hash, password):
        audit.record(
            tenant_id, AuditAction.login_failure, actor_id=user.id, details={"reason": "password"}
        )
        _register_failure(db, user)
        raise AuthError()
    return PasswordStepResult(user=user, enrollment_required=not user.mfa_enabled)


# --------------------------------------------------------------------------- MFA step


def _load_pending_user(db: Session, user_id: uuid.UUID, tenant_id: uuid.UUID) -> User:
    set_tenant(db, tenant_id)
    user = db.get(User, user_id)
    if user is None or not user.is_active or _is_locked(user):
        raise AuthError()
    return user


def _check_totp(db: Session, user: User, code: str) -> bool:
    if not user.totp_secret_enc:
        return False
    secret = decrypt_field(load_keyring(db, user.tenant_id), TOTP_FIELD, user.totp_secret_enc)
    step = verify_totp(secret, code, user.totp_last_step)
    if step is None:
        return False
    user.totp_last_step = step
    return True


def _use_recovery_code(db: Session, user: User, code: str) -> bool:
    normalized = normalize_recovery_code(code)
    if len(normalized) != 10:
        return False
    rows = db.scalars(
        select(RecoveryCode).where(RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_(None))
    ).all()
    for rc in rows:
        if verify_password(rc.code_hash, normalized):
            rc.used_at = _now()
            return True
    return False


def verify_second_factor(
    db: Session, user: User, *, code: str | None, recovery_code: str | None, purpose: str
) -> None:
    """Verify TOTP or a recovery code; counts failures toward lockout. ``purpose`` is
    ``login`` or ``reauth`` (only affects audit actions)."""
    check_rate(
        (ip_key("mfa", _ip()), MFA_PER_IP),
        (account_key("mfa", str(user.id)), MFA_PER_ACCOUNT),
        tenant_id=user.tenant_id,
    )
    ok = False
    used_recovery = False
    if code:
        ok = _check_totp(db, user, code)
    elif recovery_code:
        ok = used_recovery = _use_recovery_code(db, user, recovery_code)
    if not ok:
        audit.record(
            user.tenant_id,
            AuditAction.mfa_failure if purpose == "login" else AuditAction.reauth_failure,
            actor_id=user.id,
            details={"method": "recovery_code" if recovery_code else "totp"},
        )
        _register_failure(db, user)
        raise AuthError()
    if used_recovery:
        remaining = db.scalar(
            select(RecoveryCode.id)
            .where(RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_(None))
            .limit(1)
        )
        audit.record(
            user.tenant_id,
            AuditAction.recovery_code_used,
            actor_id=user.id,
            details={"codes_remaining": remaining is not None},
        )


def complete_mfa_login(
    db: Session,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    *,
    code: str | None,
    recovery_code: str | None,
) -> IssuedSession:
    user = _load_pending_user(db, user_id, tenant_id)
    if not user.mfa_enabled:
        raise AuthError()
    verify_second_factor(db, user, code=code, recovery_code=recovery_code, purpose="login")
    audit.record(tenant_id, AuditAction.mfa_success, actor_id=user.id)
    return create_session(db, user)


@dataclass
class EnrollmentStart:
    otpauth_uri: str
    qr_svg_data_uri: str
    secret: str


def start_enrollment(db: Session, user_id: uuid.UUID, tenant_id: uuid.UUID) -> EnrollmentStart:
    user = _load_pending_user(db, user_id, tenant_id)
    if user.mfa_enabled:
        raise AuthError()
    secret = new_totp_secret()
    user.totp_secret_enc = encrypt_field(load_keyring(db, tenant_id), TOTP_FIELD, secret)
    user.totp_last_step = None
    db.commit()
    audit.record(tenant_id, AuditAction.mfa_enroll_start, actor_id=user.id)
    uri = totp_uri(secret, user.email)
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=8)
    buf = io.BytesIO()
    img.save(buf)
    data_uri = "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()
    return EnrollmentStart(otpauth_uri=uri, qr_svg_data_uri=data_uri, secret=secret)


def confirm_enrollment(
    db: Session, user_id: uuid.UUID, tenant_id: uuid.UUID, code: str
) -> tuple[IssuedSession, list[str]]:
    user = _load_pending_user(db, user_id, tenant_id)
    if user.mfa_enabled or not user.totp_secret_enc:
        raise AuthError()
    check_rate(
        (ip_key("mfa", _ip()), MFA_PER_IP),
        (account_key("mfa", str(user.id)), MFA_PER_ACCOUNT),
        tenant_id=tenant_id,
    )
    if not _check_totp(db, user, code):
        audit.record(
            tenant_id, AuditAction.mfa_failure, actor_id=user.id, details={"stage": "enroll"}
        )
        _register_failure(db, user)
        raise AuthError()
    user.mfa_enabled = True
    codes = generate_recovery_codes()
    db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
    db.add_all(
        RecoveryCode(
            tenant_id=tenant_id,
            user_id=user.id,
            code_hash=hash_password(normalize_recovery_code(c)),
        )
        for c in codes
    )
    db.flush()
    audit.record(tenant_id, AuditAction.mfa_enrolled, actor_id=user.id)
    return create_session(db, user), codes


# --------------------------------------------------------------------------- sessions


def _issue_refresh(db: Session, session: UserSession) -> str:
    token = random_token(32)
    db.add(
        RefreshToken(
            tenant_id=session.tenant_id,
            session_id=session.id,
            token_hash=token_hash(token),
            expires_at=session.expires_at,
        )
    )
    return token


def create_session(db: Session, user: User, *, mfa: str = "totp") -> IssuedSession:
    s = get_settings()
    now = _now()
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    session = UserSession(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.id,
        # Absolute session lifetime (default 12 h) caps the 7-day refresh-token lifetime.
        expires_at=now
        + timedelta(seconds=min(s.refresh_token_ttl_seconds, s.session_absolute_seconds)),
        last_seen_at=now,
        mfa_verified_at=now,
        ip=_ip(),
        user_agent=_ua(),
    )
    db.add(session)
    db.flush()
    refresh = _issue_refresh(db, session)
    db.commit()
    audit.record(
        user.tenant_id,
        AuditAction.login_success,
        actor_id=user.id,
        resource_type="user_sessions",
        resource_id=session.id,
        details={"mfa": mfa},
    )
    return IssuedSession(session, create_access_token(user.id, user.tenant_id, session.id), refresh)


def mfa_exemption_applies(user: User) -> bool:
    """True only when the demo exemption is explicitly enabled, the environment is not
    production and the account itself is flagged. Default configuration: never."""
    s = get_settings()
    return bool(s.mfa_exemption_enabled and not s.is_production and user.mfa_exempt)


def login_exempt(db: Session, user: User) -> IssuedSession:
    """Password-only login for an account an operator explicitly exempted from MFA."""
    if not mfa_exemption_applies(user):
        raise AuthError()
    return create_session(db, user, mfa="exempt")


def rotate_refresh(db: Session, refresh_token: str) -> IssuedSession:
    """Rotate a refresh token. Presenting an already-used token revokes the whole family."""
    check_rate((ip_key("refresh", _ip()), REFRESH_PER_IP))
    digest = token_hash(refresh_token)
    tenant_id = db.execute(text("SELECT rs_auth_find_refresh_tenant(:h)"), {"h": digest}).scalar()
    if not isinstance(tenant_id, uuid.UUID):
        raise AuthError()
    set_tenant(db, tenant_id)
    row = db.scalars(
        select(RefreshToken).where(RefreshToken.token_hash == digest).with_for_update()
    ).first()
    if row is None:
        raise AuthError()
    session = db.get(UserSession, row.session_id, with_for_update=True)
    now = _now()
    if session is None:
        raise AuthError()
    if row.used_at is not None:
        if session.revoked_at is None:
            session.revoked_at = now
            session.revoked_reason = "refresh_reuse"
        db.commit()
        audit.record(
            tenant_id,
            AuditAction.refresh_reuse,
            actor_id=session.user_id,
            resource_type="user_sessions",
            resource_id=session.id,
        )
        raise AuthError()
    if session.revoked_at is not None or session.expires_at <= now or row.expires_at <= now:
        raise AuthError()
    if now - session.last_seen_at > timedelta(seconds=get_settings().session_idle_seconds):
        session.revoked_at, session.revoked_reason = now, "idle_timeout"
        db.commit()
        raise AuthError()
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise AuthError()
    row.used_at = now
    session.last_seen_at = now
    new_refresh = _issue_refresh(db, session)
    db.commit()
    return IssuedSession(session, create_access_token(user.id, tenant_id, session.id), new_refresh)


def revoke_session(db: Session, session: UserSession, *, actor_id: uuid.UUID, reason: str) -> None:
    if session.revoked_at is None:
        session.revoked_at = _now()
        session.revoked_reason = reason[:64]
        db.commit()
    audit.record(
        session.tenant_id,
        AuditAction.session_revoked if reason != "logout" else AuditAction.logout,
        actor_id=actor_id,
        resource_type="user_sessions",
        resource_id=session.id,
        details={"reason": reason, "target_user_id": str(session.user_id)},
    )


def revoke_all_sessions(db: Session, user: User, *, actor_id: uuid.UUID, reason: str) -> int:
    sessions = db.scalars(
        select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
    ).all()
    for s in sessions:
        revoke_session(db, s, actor_id=actor_id, reason=reason)
    return len(sessions)


def reauthenticate(
    db: Session, user: User, session: UserSession, *, code: str | None, recovery_code: str | None
) -> None:
    verify_second_factor(db, user, code=code, recovery_code=recovery_code, purpose="reauth")
    session.mfa_verified_at = _now()
    db.commit()
    audit.record(user.tenant_id, AuditAction.reauth_success, actor_id=user.id)


# --------------------------------------------------------------------------- invitations


@dataclass
class CreatedInvitation:
    invitation: Invitation
    token: str


def create_invitation(
    db: Session, tenant_id: uuid.UUID, email: str, role: str, invited_by: uuid.UUID | None
) -> CreatedInvitation:
    token = random_token(32)
    inv = Invitation(
        tenant_id=tenant_id,
        email=email.strip().lower(),
        role=role,
        token_hash=token_hash(token),
        invited_by=invited_by,
        expires_at=_now() + timedelta(seconds=get_settings().invitation_ttl_seconds),
    )
    db.add(inv)
    db.flush()
    return CreatedInvitation(inv, token)


def _find_invitation(db: Session, token: str, kind: str = "invite") -> Invitation:
    check_rate((ip_key("invite", _ip()), INVITE_PER_IP))
    digest = token_hash(token)
    tenant_id = db.execute(
        text("SELECT rs_auth_find_invitation_tenant(:h)"), {"h": digest}
    ).scalar()
    if not isinstance(tenant_id, uuid.UUID):
        platform = _platform_tenant(db)
        if platform:
            audit.record(platform, AuditAction.invitation_failure, details={"reason": "invalid"})
        raise AuthError("Invalid or expired invitation")
    set_tenant(db, tenant_id)
    inv = db.scalars(
        select(Invitation).where(Invitation.token_hash == digest).with_for_update()
    ).first()
    if inv is None or inv.kind != kind or inv.used_at or inv.revoked_at or inv.expires_at <= _now():
        raise AuthError("Invalid or expired invitation")
    return inv


def inspect_invitation(db: Session, token: str) -> tuple[Invitation, Tenant]:
    inv = _find_invitation(db, token)
    tenant = db.get(Tenant, inv.tenant_id)
    assert tenant is not None
    return inv, tenant


def accept_invitation(db: Session, token: str, display_name: str, password: str) -> User:
    inv = _find_invitation(db, token)
    errors = password_policy_errors(password, email=inv.email)
    if errors:
        raise PolicyError(errors)
    exists = db.execute(text("SELECT 1 FROM rs_auth_find_user(:e)"), {"e": inv.email}).first()
    if exists:
        raise AuthError("Invalid or expired invitation")
    user = User(
        tenant_id=inv.tenant_id,
        email=inv.email,
        display_name=display_name.strip()[:200],
        role=inv.role,
        password_hash=hash_password(password),
        mfa_enabled=False,
    )
    db.add(user)
    inv.used_at = _now()
    db.commit()
    audit.record(
        inv.tenant_id,
        AuditAction.invitation_accepted,
        actor_id=user.id,
        resource_type="invitations",
        resource_id=inv.id,
    )
    return user


def change_password(
    db: Session, user: User, session: UserSession, current_password: str, new_password: str
) -> None:
    """Own password change. Wrong current password counts as a failed login (lockout applies)."""
    check_rate((account_key("pwchange", user.email), LOGIN_PER_ACCOUNT))
    if not verify_password(user.password_hash, current_password):
        audit.record(
            user.tenant_id,
            AuditAction.login_failure,
            actor_id=user.id,
            details={"reason": "password_change"},
        )
        _register_failure(db, user)
        raise AuthError()
    errors = password_policy_errors(new_password, email=user.email)
    if errors:
        raise PolicyError(errors)
    if verify_password(user.password_hash, new_password):
        raise PolicyError(["The new password must differ from the current one"])
    user.password_hash = hash_password(new_password)
    db.commit()
    others = db.scalars(
        select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
            UserSession.id != session.id,
        )
    ).all()
    for s in others:
        revoke_session(db, s, actor_id=user.id, reason="password_changed")
    audit.record(
        user.tenant_id,
        AuditAction.password_changed,
        actor_id=user.id,
        resource_type="users",
        resource_id=user.id,
        details={"sessions_revoked": len(others)},
    )


def revoke_other_sessions(db: Session, user: User, keep: UserSession) -> int:
    others = db.scalars(
        select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
            UserSession.id != keep.id,
        )
    ).all()
    for s in others:
        revoke_session(db, s, actor_id=user.id, reason="revoked_others")
    audit.record(
        user.tenant_id,
        AuditAction.sessions_revoked_bulk,
        actor_id=user.id,
        resource_type="users",
        resource_id=user.id,
        details={"count": len(others), "scope": "own_other_sessions"},
    )
    return len(others)
