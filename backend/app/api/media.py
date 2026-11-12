"""Shared evidence streaming for ``/api/media/{id}`` and ``/api/evidence/{id}/content``:
byte ranges (206) for video seeking, explicit 410 for purged or missing files, no storage
paths in any response."""

from __future__ import annotations

import re
from collections.abc import Iterator

from fastapi import HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from app.core import metrics
from app.core.audit import AuditAction
from app.core.crypto import CryptoError
from app.deps import Principal
from app.models import Evidence
from app.services import evidence as evidence_service

_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")
MAX_RANGE_SOURCE = 128 * 1024 * 1024  # decrypted size we are willing to buffer for a range


def open_or_gone(principal: Principal, ev: Evidence, variant: str) -> tuple[bytes, Iterator[bytes]]:
    """First decrypted chunk + the rest. Purged/missing evidence -> audited 410. The time to the
    first chunk is recorded as ``rs_evidence_read_seconds`` (variant, outcome)."""
    with metrics.timed(metrics.EVIDENCE_READ, variant=variant, outcome="ok") as measured:
        stream = evidence_service.open_decrypted(principal.keyring, ev, variant)
        try:
            return next(stream), stream
        except evidence_service.EvidencePurgedError as exc:
            measured["outcome"] = "purged"
            principal.audit(
                AuditAction.evidence_missing,
                resource_type="evidence",
                resource_id=ev.id,
                details={"state": "purged", "variant": variant},
            )
            raise HTTPException(410, "Proba a fost purjată și nu mai poate fi afișată.") from exc
        except FileNotFoundError as exc:
            measured["outcome"] = "missing"
            principal.audit(
                AuditAction.evidence_missing,
                resource_type="evidence",
                resource_id=ev.id,
                details={"state": "missing", "variant": variant},
            )
            raise HTTPException(410, "Fișierul probei lipsește din stocare.") from exc
        except StopIteration:
            return b"", iter(())
        except evidence_service.StorageUnavailableError:
            measured["outcome"] = "unavailable"
            raise
        except CryptoError as exc:
            measured["outcome"] = "crypto_error"
            raise HTTPException(500, "Evidence unavailable") from exc


def respond(
    request: Request,
    first: bytes,
    rest: Iterator[bytes],
    media_type: str,
    headers: dict[str, str],
) -> Response:
    headers = {**headers, "Accept-Ranges": "bytes"}
    m = _RANGE.match(request.headers.get("range", "").strip())
    if not m or (not m.group(1) and not m.group(2)):
        # No (or an unsupported multi-) range: stream everything.
        def body() -> Iterator[bytes]:
            yield first
            yield from rest

        return StreamingResponse(body(), media_type=media_type, headers=headers)
    data = bytearray(first)
    for chunk in rest:
        data += chunk
        if len(data) > MAX_RANGE_SOURCE:
            raise HTTPException(413, "Range requests are not supported for files this large")
    total = len(data)
    if m.group(1):
        start = int(m.group(1))
        end = min(int(m.group(2)), total - 1) if m.group(2) else total - 1
    else:  # suffix range: the last N bytes
        start, end = max(total - int(m.group(2)), 0), total - 1
    if start >= total or start > end:
        return Response(status_code=416, headers={**headers, "Content-Range": f"bytes */{total}"})
    return Response(
        bytes(data[start : end + 1]),
        status_code=206,
        media_type=media_type,
        headers={**headers, "Content-Range": f"bytes {start}-{end}/{total}"},
    )
