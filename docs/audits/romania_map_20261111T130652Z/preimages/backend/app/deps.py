"""FastAPI dependencies: DB session, authenticated principal, permissions, re-authentication.

Tenant identity is taken *only* from the verified access token (and re-checked against the
session row). No endpoint accepts a tenant id from the client.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, NoReturn

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import audit
from app.core.audit import AuditAction
from app.core.crypto import TenantKeyring
from app.core.http import ACCESS, client_ip, cookie_name
from app.core.policy import Permission, has_permission
from app.core.security import decode_access_token
from app.db import get_sessionmaker, set_tenant
from app.models import Role, User, UserSession
from app.services.ingest_auth import IngestAuthError, ServicePrincipal, authenticate
from app.services.keys import load_keyring

LAST_SEEN_RESOLUTION = timedelta(seconds=60)


def get_db() -> Iterator[Session]:
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@dataclass
class Principal:
    user: User
    session: UserSession
    db: Session = field(repr=False)
    _keyring: TenantKeyring | None = field(default=None, repr=False)

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id

    @property
    def tenant_id(self) -> uuid.UUID:
        return self.user.tenant_id

    @property
    def role(self) -> Role:
        return self.user.role

    @property
    def keyring(self) -> TenantKeyring:
        if self._keyring is None:
            self._keyring = load_keyring(self.db, self.tenant_id)
        return self._keyring

    def audit(self, action: AuditAction | str, **kwargs: Any) -> None:
        audit.record(self.tenant_id, action, actor_id=self.user_id, **kwargs)


def _unauthorized() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")


def get_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    token = request.cookies.get(cookie_name(ACCESS))
    if not token:
        raise _unauthorized()
    try:
        claims = decode_access_token(token)
    except (jwt.InvalidTokenError, ValueError, KeyError) as exc:
        raise _unauthorized() from exc

    set_tenant(db, claims.tenant_id)
    session = db.get(UserSession, claims.session_id)
    now = datetime.now(UTC)
    if (
        session is None
        or session.user_id != claims.user_id
        or session.revoked_at is not None
        or session.expires_at <= now
    ):
        raise _unauthorized()
    user = db.get(User, claims.user_id)
    if user is None or not user.is_active or user.tenant_id != claims.tenant_id:
        raise _unauthorized()
    if now - session.last_seen_at > timedelta(seconds=get_settings().session_idle_seconds):
        # Idle timeout: nobody used this session for too long. Ends it for good.
        session.revoked_at, session.revoked_reason = now, "idle_timeout"
        db.commit()
        raise _unauthorized()
    if now - session.last_seen_at > LAST_SEEN_RESOLUTION:
        session.last_seen_at = now
        db.commit()
    return Principal(user=user, session=session, db=db)


def require(permission: Permission) -> Callable[..., Principal]:
    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if not has_permission(principal.role, permission):
            principal.audit(AuditAction.access_denied, details={"permission": permission.value})
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
        return principal

    return dependency


def require_fresh_mfa(principal: Principal) -> None:
    """Sensitive actions need an MFA verification within the re-auth window. Only when the
    explicit (off-by-default, never-in-production) demo exemption applies is the check skipped."""
    from app.services.auth import mfa_exemption_applies

    if mfa_exemption_applies(principal.user):
        return
    window = timedelta(seconds=get_settings().reauth_window_seconds)
    if datetime.now(UTC) - principal.session.mfa_verified_at > window:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "reauth_required")


def not_found(principal: Principal, table: str, resource_id: uuid.UUID) -> NoReturn:
    """Raise 404 for a missing object; if it exists in another tenant, audit the probe in both
    tenants' chains. The response is identical either way, so existence never leaks."""
    owner = principal.db.execute(
        text("SELECT rs_resource_tenant(:t, :id)"), {"t": table, "id": resource_id}
    ).scalar()
    if isinstance(owner, uuid.UUID) and owner != principal.tenant_id:
        details = {"table": table, "actor_tenant_id": str(principal.tenant_id)}
        principal.audit(
            AuditAction.cross_tenant_access,
            resource_type=table,
            resource_id=resource_id,
            details=details,
        )
        audit.record(
            owner,
            AuditAction.cross_tenant_access,
            actor_id=principal.user_id,
            resource_type=table,
            resource_id=resource_id,
            details=details,
        )
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")


async def get_service_principal(
    request: Request, db: Session = Depends(get_db)
) -> ServicePrincipal:
    """Authenticate a signed pipeline request (HMAC). Cookies are never consulted here.

    The body is read once, with a hard size cap, and cached so the route can still parse it."""
    limit = get_settings().ingest_max_body_bytes
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Request too large")
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > limit:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Request too large")
        chunks.append(chunk)
    body = b"".join(chunks)
    request._body = body

    raw_path = request.scope.get("raw_path") or request.url.path.encode()
    query = request.scope.get("query_string", b"")
    target = raw_path.decode("latin-1") + (f"?{query.decode('latin-1')}" if query else "")
    try:
        return await run_in_threadpool(
            authenticate,
            db,
            method=request.method,
            target=target,
            headers={k.lower(): v for k, v in request.headers.items()},
            body=body,
            client_ip=client_ip(request),
        )
    except IngestAuthError as exc:
        if exc.rate_limited:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many requests",
                headers={"Retry-After": str(exc.retry_after)},
            ) from exc
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature") from exc
