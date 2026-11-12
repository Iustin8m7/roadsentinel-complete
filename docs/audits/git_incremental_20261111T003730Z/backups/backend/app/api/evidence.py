"""Evidence metadata and content. Content is reachable only through short-lived signed URLs
(HMAC over purpose, evidence id, variant, user id and expiry) *and* a valid session cookie of
that same user. Originals (unblurred) additionally need an active four-eyes grant at view time."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.alerts import PLATE_FIELD, get_visible_alert
from app.config import get_settings
from app.core.audit import AuditAction
from app.core.crypto import CryptoError, decrypt_field, sign_url_params, verify_url_params
from app.core.policy import Permission
from app.deps import Principal, not_found, require, require_fresh_mfa
from app.models import ApprovalKind, Evidence
from app.schemas.ops import EvidenceAccessIn, EvidenceOut, SignedUrlOut
from app.services import evidence as evidence_service
from app.services.approvals import active_grant

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

VIEW, EXPORT = "view", "export"


def _key() -> bytes:
    return get_settings().url_signing_key.get_secret_value().encode()


def get_visible_evidence(principal: Principal, evidence_id: uuid.UUID) -> Evidence:
    """Alert evidence only; camera recordings (no parent alert) are served through /media."""
    ev = principal.db.get(Evidence, evidence_id)
    if ev is None or ev.alert_id is None:
        not_found(principal, "evidence", evidence_id)
    get_visible_alert(principal, ev.alert_id)  # patrol scoping via the parent alert
    return ev


def _alert_id(ev: Evidence) -> uuid.UUID:
    assert ev.alert_id is not None  # guaranteed by get_visible_evidence / the list query
    return ev.alert_id


def _signed_url(principal: Principal, ev: Evidence, variant: str, purpose: str) -> SignedUrlOut:
    exp = int(time.time()) + get_settings().signed_url_ttl_seconds
    resource = f"{ev.id}:{variant}"
    sig = sign_url_params(_key(), purpose, resource, str(principal.user_id), exp)
    query = urlencode({"variant": variant, "purpose": purpose, "exp": exp, "sig": sig})
    return SignedUrlOut(
        url=f"/api/evidence/{ev.id}/content?{query}",
        expires_at=datetime.fromtimestamp(exp, UTC),
    )


@router.get("", response_model=list[EvidenceOut])
def list_for_alert(
    alert_id: uuid.UUID, principal: Principal = Depends(require(Permission.evidence_read))
) -> list[EvidenceOut]:
    alert = get_visible_alert(principal, alert_id)
    rows = principal.db.scalars(select(Evidence).where(Evidence.alert_id == alert.id)).all()
    return [_to_out(principal, ev) for ev in rows]


def require_present(ev: Evidence) -> None:
    """Retention removed the file(s); the row stays for chain of custody."""
    if ev.purged_at is not None:
        raise HTTPException(410, "evidence_purged: removed by the retention policy")


def require_original(principal: Principal, ev: Evidence) -> None:
    """Pipeline evidence has a single stored copy: there is nothing to unblur or export."""
    if not ev.has_original:
        principal.audit(
            AuditAction.access_denied,
            resource_type="evidence",
            resource_id=ev.id,
            details={"reason": "no_original"},
        )
        raise HTTPException(409, "no_original: no distinct original exists for this evidence")


def _to_out(principal: Principal, ev: Evidence) -> EvidenceOut:
    grant = active_grant(
        principal.db, kind=ApprovalKind.unblur, resource_id=ev.id, user_id=principal.user_id
    )
    out = EvidenceOut(
        id=ev.id,
        alert_id=_alert_id(ev),
        kind=ev.kind,
        content_type=ev.content_type,
        size_bytes=ev.size_bytes,
        sha256=ev.sha256,
        created_at=ev.created_at,
        redaction=ev.redaction,
        has_original=ev.has_original,
        unblur_grant_expires_at=grant.grant_expires_at if grant else None,
    )
    if grant:
        alert = get_visible_alert(principal, _alert_id(ev))
        if alert.plate_enc is not None:
            out.plate = decrypt_field(principal.keyring, PLATE_FIELD, alert.plate_enc)
    return out


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence(
    evidence_id: uuid.UUID, principal: Principal = Depends(require(Permission.evidence_read))
) -> EvidenceOut:
    ev = get_visible_evidence(principal, evidence_id)
    out = _to_out(principal, ev)
    if out.plate is not None:
        principal.audit(
            AuditAction.evidence_viewed,
            resource_type="evidence",
            resource_id=ev.id,
            details={"variant": "plate_unmasked"},
        )
    return out


@router.post("/{evidence_id}/access", response_model=SignedUrlOut)
def request_access(
    evidence_id: uuid.UUID,
    body: EvidenceAccessIn,
    principal: Principal = Depends(require(Permission.evidence_read)),
) -> SignedUrlOut:
    ev = get_visible_evidence(principal, evidence_id)
    require_present(ev)
    if body.variant == "original":
        require_original(principal, ev)
    if body.variant == "original" and not active_grant(
        principal.db, kind=ApprovalKind.unblur, resource_id=ev.id, user_id=principal.user_id
    ):
        principal.audit(
            AuditAction.access_denied,
            resource_type="evidence",
            resource_id=ev.id,
            details={"reason": "no_unblur_grant"},
        )
        raise HTTPException(403, "An approved unblur request is required")
    url = _signed_url(principal, ev, body.variant, VIEW)
    principal.audit(
        AuditAction.evidence_url_issued,
        resource_type="evidence",
        resource_id=ev.id,
        details={"variant": body.variant},
    )
    return url


@router.post("/{evidence_id}/export", response_model=SignedUrlOut)
def export(
    evidence_id: uuid.UUID, principal: Principal = Depends(require(Permission.evidence_read))
) -> SignedUrlOut:
    require_fresh_mfa(principal)
    ev = get_visible_evidence(principal, evidence_id)
    require_present(ev)
    require_original(principal, ev)
    if not active_grant(
        principal.db, kind=ApprovalKind.export, resource_id=ev.id, user_id=principal.user_id
    ):
        principal.audit(
            AuditAction.access_denied,
            resource_type="evidence",
            resource_id=ev.id,
            details={"reason": "no_export_grant"},
        )
        raise HTTPException(403, "An approved export request is required")
    url = _signed_url(principal, ev, "original", EXPORT)
    principal.audit(
        AuditAction.evidence_url_issued,
        resource_type="evidence",
        resource_id=ev.id,
        details={"variant": "original", "purpose": EXPORT},
    )
    return url


@router.get("/{evidence_id}/content")
def content(
    evidence_id: uuid.UUID,
    variant: str = Query(pattern="^(redacted|original)$"),
    purpose: str = Query(pattern="^(view|export)$"),
    exp: int = Query(),
    sig: str = Query(max_length=100),
    principal: Principal = Depends(require(Permission.evidence_read)),
) -> StreamingResponse:
    if not verify_url_params(
        _key(), purpose, f"{evidence_id}:{variant}", str(principal.user_id), exp, sig
    ):
        raise HTTPException(403, "Invalid or expired link")
    ev = get_visible_evidence(principal, evidence_id)
    require_present(ev)
    # Grants are re-checked at view time: revocation or expiry takes effect immediately.
    if variant == "original":
        require_original(principal, ev)
        kind = ApprovalKind.export if purpose == EXPORT else ApprovalKind.unblur
        if not active_grant(principal.db, kind=kind, resource_id=ev.id, user_id=principal.user_id):
            raise HTTPException(403, "Grant expired or revoked")
    keyring = principal.keyring
    stream = evidence_service.open_decrypted(keyring, ev, variant)
    try:
        first = next(stream)
    except (CryptoError, FileNotFoundError, StopIteration) as exc:
        raise HTTPException(500, "Evidence unavailable") from exc
    principal.audit(
        AuditAction.evidence_exported if purpose == EXPORT else AuditAction.evidence_viewed,
        resource_type="evidence",
        resource_id=ev.id,
        details={"variant": variant},
    )

    def body() -> object:
        yield first
        yield from stream

    disposition = "attachment" if purpose == EXPORT else "inline"
    return StreamingResponse(
        body(),  # type: ignore[arg-type]
        media_type=ev.content_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="evidence-{ev.id}-{variant}"',
            "Cache-Control": "no-store",
        },
    )
