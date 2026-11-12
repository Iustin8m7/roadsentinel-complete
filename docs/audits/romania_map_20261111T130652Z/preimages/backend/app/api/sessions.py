"""The caller's own sessions/devices. Admin-level session management lives in users.py."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.deps import Principal, get_principal, not_found
from app.models import UserSession
from app.schemas.auth import SessionOut
from app.services import auth as auth_service

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def to_out(s: UserSession, current_id: uuid.UUID | None = None) -> SessionOut:
    return SessionOut(
        id=s.id,
        user_id=s.user_id,
        created_at=s.created_at,
        last_seen_at=s.last_seen_at,
        expires_at=s.expires_at,
        ip=s.ip,
        user_agent=s.user_agent,
        revoked_at=s.revoked_at,
        revoked_reason=s.revoked_reason,
        current=s.id == current_id,
    )


@router.get("", response_model=list[SessionOut])
def list_my_sessions(principal: Principal = Depends(get_principal)) -> list[SessionOut]:
    rows = principal.db.scalars(
        select(UserSession)
        .where(UserSession.user_id == principal.user_id)
        .order_by(UserSession.last_seen_at.desc())
        .limit(50)
    ).all()
    return [to_out(s, principal.session.id) for s in rows]


@router.delete("/{session_id}", status_code=204)
def revoke_my_session(session_id: uuid.UUID, principal: Principal = Depends(get_principal)) -> None:
    s = principal.db.get(UserSession, session_id)
    if s is None or s.user_id != principal.user_id:
        not_found(principal, "user_sessions", session_id)
    auth_service.revoke_session(principal.db, s, actor_id=principal.user_id, reason="user_revoked")


@router.post("/revoke-others")
def revoke_other_sessions(principal: Principal = Depends(get_principal)) -> dict[str, int]:
    """Sign out every other device of the caller (lost phone, shared PC)."""
    n = auth_service.revoke_other_sessions(principal.db, principal.user, principal.session)
    return {"revoked": n}
