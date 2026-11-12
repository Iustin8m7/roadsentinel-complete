"""Signed, filter-bound cursors for stable alert search pagination."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from app.config import get_settings


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def filter_fingerprint(filters: dict[str, Any]) -> str:
    canonical = json.dumps(filters, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _key() -> bytes:
    secret = get_settings().url_signing_key.get_secret_value().encode("utf-8")
    return hmac.new(secret, b"roadsentinel:alert-search-cursor:v1", hashlib.sha256).digest()


def encode_cursor(
    *, tenant_id: UUID, filters: dict[str, Any], is_decided: bool, priority_rank: int,
    detected_at: datetime, number: int,
) -> str:
    payload = {
        "v": 1,
        "tenant": str(tenant_id),
        "filter": filter_fingerprint(filters),
        "decided": bool(is_decided),
        "priority": int(priority_rank),
        "at": detected_at.astimezone(UTC).isoformat(),
        "number": int(number),
        "exp": int(time.time()) + 3600,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    encoded = _b64(raw)
    signature = hmac.new(_key(), encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_b64(signature)}"


def decode_cursor(
    cursor: str, *, tenant_id: UUID, filters: dict[str, Any]
) -> tuple[bool, int, datetime, int]:
    try:
        encoded, supplied = cursor.split(".", 1)
        expected = _b64(hmac.new(_key(), encoded.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(supplied, expected):
            raise ValueError("signature")
        payload = json.loads(_unb64(encoded))
        if (
            payload.get("v") != 1
            or payload.get("tenant") != str(tenant_id)
            or payload.get("filter") != filter_fingerprint(filters)
            or type(payload.get("exp")) is not int
            or payload["exp"] <= int(time.time())
            or type(payload.get("decided")) is not bool
            or type(payload.get("priority")) is not int
            or type(payload.get("number")) is not int
            or payload["priority"] not in range(4)
            or payload["number"] <= 0
        ):
            raise ValueError("scope")
        detected_at = datetime.fromisoformat(payload["at"])
        if detected_at.tzinfo is None:
            raise ValueError("timestamp")
        return payload["decided"], payload["priority"], detected_at, payload["number"]
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(400, "Invalid search cursor") from exc
