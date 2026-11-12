from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select

from app.config import get_settings
from app.core.audit import AuditAction
from app.core.policy import Permission
from app.deps import Principal, get_principal, require
from app.models import PushSubscription
from app.schemas.ops import PushSubscriptionIn, VapidKeyOut

router = APIRouter(prefix="/api/push", tags=["push"])


@router.get("/vapid-public-key", response_model=VapidKeyOut)
def vapid_public_key(_: Principal = Depends(get_principal)) -> VapidKeyOut:
    return VapidKeyOut(public_key=get_settings().vapid_public_key)


@router.post("/subscriptions", status_code=204)
def subscribe(
    body: PushSubscriptionIn, principal: Principal = Depends(require(Permission.push_subscribe))
) -> None:
    existing = principal.db.scalars(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    ).first()
    if existing is None:
        principal.db.add(
            PushSubscription(
                tenant_id=principal.tenant_id, user_id=principal.user_id, **body.model_dump()
            )
        )
    else:
        existing.user_id, existing.p256dh, existing.auth = principal.user_id, body.p256dh, body.auth
    principal.db.commit()
    principal.audit(AuditAction.push_subscribed)


@router.delete("/subscriptions", status_code=204)
def unsubscribe_all(principal: Principal = Depends(get_principal)) -> None:
    """Called on logout so a shared device stops receiving this user's notifications."""
    principal.db.execute(
        delete(PushSubscription).where(PushSubscription.user_id == principal.user_id)
    )
    principal.db.commit()
