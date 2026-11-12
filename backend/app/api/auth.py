from __future__ import annotations

from datetime import timedelta

import jwt
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.http import (
    ACCESS,
    CSRF,
    MFA,
    REFRESH,
    clear_cookie,
    cookie_name,
    new_csrf_token,
    set_cookie,
)
from app.core.policy import permissions_for
from app.core.security import (
    MfaPendingClaims,
    create_mfa_pending_token,
    decode_mfa_pending_token,
)
from app.deps import Principal, get_db, get_principal, require_fresh_mfa
from app.models import Tenant
from app.schemas.auth import (
    CsrfOut,
    EnrollConfirmIn,
    EnrollConfirmOut,
    EnrollStartOut,
    InvitationAcceptIn,
    InvitationInspectIn,
    InvitationInspectOut,
    LoginIn,
    LoginOut,
    MeOut,
    MfaIn,
    PasswordChangeIn,
    ResetAcceptIn,
    ResetInspectOut,
)
from app.services import account_reset
from app.services import auth as auth_service
from app.services.auth import AuthError, IssuedSession

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookies(response: Response, issued: IssuedSession) -> None:
    s = get_settings()
    set_cookie(response, ACCESS, issued.access_token, s.access_token_ttl_seconds)
    set_cookie(response, REFRESH, issued.refresh_token, s.refresh_token_ttl_seconds)
    clear_cookie(response, MFA)


def _clear_all(response: Response) -> None:
    for kind in (ACCESS, REFRESH, MFA):
        clear_cookie(response, kind)


def _pending(request: Request, *, enrollment: bool) -> MfaPendingClaims:
    token = request.cookies.get(cookie_name(MFA))
    if not token:
        raise AuthError()
    try:
        claims = decode_mfa_pending_token(token)
    except (jwt.InvalidTokenError, ValueError, KeyError) as exc:
        raise AuthError() from exc
    if claims.enrollment != enrollment:
        raise AuthError()
    return claims


@router.get("/csrf", response_model=CsrfOut)
def csrf(request: Request, response: Response) -> CsrfOut:
    token = request.cookies.get(cookie_name(CSRF)) or new_csrf_token()
    set_cookie(response, CSRF, token, 12 * 3600)
    return CsrfOut(csrf_token=token)


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> LoginOut:
    result = auth_service.login_password(db, body.email, body.password)
    if auth_service.mfa_exemption_applies(result.user):
        _set_session_cookies(response, auth_service.login_exempt(db, result.user))
        return LoginOut(mfa_required=False, enrollment_required=False)
    token = create_mfa_pending_token(
        result.user.id, result.user.tenant_id, enrollment=result.enrollment_required
    )
    set_cookie(response, MFA, token, get_settings().mfa_pending_ttl_seconds)
    return LoginOut(enrollment_required=result.enrollment_required)


@router.post("/mfa/verify", status_code=204)
def mfa_verify(
    body: MfaIn, request: Request, response: Response, db: Session = Depends(get_db)
) -> None:
    claims = _pending(request, enrollment=False)
    issued = auth_service.complete_mfa_login(
        db, claims.user_id, claims.tenant_id, code=body.code, recovery_code=body.recovery_code
    )
    _set_session_cookies(response, issued)


@router.post("/mfa/enroll/start", response_model=EnrollStartOut)
def enroll_start(request: Request, db: Session = Depends(get_db)) -> EnrollStartOut:
    claims = _pending(request, enrollment=True)
    started = auth_service.start_enrollment(db, claims.user_id, claims.tenant_id)
    return EnrollStartOut(
        otpauth_uri=started.otpauth_uri,
        qr_svg_data_uri=started.qr_svg_data_uri,
        secret=started.secret,
    )


@router.post("/mfa/enroll/confirm", response_model=EnrollConfirmOut)
def enroll_confirm(
    body: EnrollConfirmIn, request: Request, response: Response, db: Session = Depends(get_db)
) -> EnrollConfirmOut:
    claims = _pending(request, enrollment=True)
    issued, codes = auth_service.confirm_enrollment(db, claims.user_id, claims.tenant_id, body.code)
    _set_session_cookies(response, issued)
    return EnrollConfirmOut(recovery_codes=codes)


@router.post("/refresh", status_code=204)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    token = request.cookies.get(cookie_name(REFRESH))
    try:
        if not token:
            raise AuthError()
        issued = auth_service.rotate_refresh(db, token)
    except AuthError:
        failed = Response(
            status_code=401,
            content=b'{"detail":"Invalid credentials"}',
            media_type="application/json",
        )
        _clear_all(failed)
        return failed
    _set_session_cookies(response, issued)
    response.status_code = 204
    return response


@router.post("/logout", status_code=204)
def logout(response: Response, principal: Principal = Depends(get_principal)) -> None:
    auth_service.revoke_session(
        principal.db, principal.session, actor_id=principal.user_id, reason="logout"
    )
    _clear_all(response)


@router.post("/reauth", status_code=204)
def reauth(body: MfaIn, principal: Principal = Depends(get_principal)) -> None:
    auth_service.reauthenticate(
        principal.db,
        principal.user,
        principal.session,
        code=body.code,
        recovery_code=body.recovery_code,
    )


@router.get("/me", response_model=MeOut)
def me(principal: Principal = Depends(get_principal)) -> MeOut:
    tenant = principal.db.get(Tenant, principal.tenant_id)
    assert tenant is not None
    return MeOut(
        id=principal.user_id,
        email=principal.user.email,
        display_name=principal.user.display_name,
        role=principal.role,
        tenant_id=principal.tenant_id,
        tenant_name=tenant.name,
        permissions=permissions_for(principal.role),
        session_id=principal.session.id,
        mfa_fresh_until=principal.session.mfa_verified_at
        + timedelta(seconds=get_settings().reauth_window_seconds),
    )


@router.post("/invitations/inspect", response_model=InvitationInspectOut)
def inspect_invitation(
    body: InvitationInspectIn, db: Session = Depends(get_db)
) -> InvitationInspectOut:
    inv, tenant = auth_service.inspect_invitation(db, body.token)
    return InvitationInspectOut(
        email=inv.email, role=inv.role, tenant_name=tenant.name, expires_at=inv.expires_at
    )


@router.post("/invitations/accept", response_model=LoginOut)
def accept_invitation(
    body: InvitationAcceptIn, response: Response, db: Session = Depends(get_db)
) -> LoginOut:
    user = auth_service.accept_invitation(db, body.token, body.display_name, body.password)
    token = create_mfa_pending_token(user.id, user.tenant_id, enrollment=True)
    set_cookie(response, MFA, token, get_settings().mfa_pending_ttl_seconds)
    return LoginOut(enrollment_required=True)


@router.post("/reset/inspect", response_model=ResetInspectOut)
def inspect_reset(body: InvitationInspectIn, db: Session = Depends(get_db)) -> ResetInspectOut:
    inv, user = account_reset.inspect_reset(db, body.token)
    return ResetInspectOut(email=user.email, reset_mfa=inv.reset_mfa, expires_at=inv.expires_at)


@router.post("/reset/accept", status_code=204)
def accept_reset(body: ResetAcceptIn, response: Response, db: Session = Depends(get_db)) -> None:
    """Set a new password with a single-use recovery token. Nobody is logged in by this: the user
    signs in normally afterwards (and enrolls MFA again if it was reset)."""
    account_reset.accept_reset(db, body.token, body.password)
    _clear_all(response)


@router.post("/password", status_code=204)
def change_password(body: PasswordChangeIn, principal: Principal = Depends(get_principal)) -> None:
    """Change your own password: current password + fresh MFA; other sessions are revoked."""
    require_fresh_mfa(principal)
    auth_service.change_password(
        principal.db, principal.user, principal.session, body.current_password, body.new_password
    )
