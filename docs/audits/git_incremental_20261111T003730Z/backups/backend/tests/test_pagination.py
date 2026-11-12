from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services import pagination


def token(**overrides):
    args = {
        "tenant_id": uuid4(),
        "filters": {"event_types": ["wrong_way"], "status": None},
        "is_decided": False,
        "priority_rank": 0,
        "detected_at": datetime(2026, 11, 6, tzinfo=UTC),
        "number": 42,
    }
    args.update(overrides)
    return args, pagination.encode_cursor(**args)


def test_signed_cursor_round_trip_is_scoped_to_tenant_and_filters() -> None:
    args, value = token()
    decoded = pagination.decode_cursor(
        value, tenant_id=args["tenant_id"], filters=args["filters"]
    )
    assert decoded == (False, 0, args["detected_at"], 42)
    with pytest.raises(HTTPException) as foreign_tenant:
        pagination.decode_cursor(value, tenant_id=uuid4(), filters=args["filters"])
    assert foreign_tenant.value.status_code == 400
    with pytest.raises(HTTPException) as changed_filter:
        pagination.decode_cursor(
            value, tenant_id=args["tenant_id"], filters={"event_types": ["congestion"]}
        )
    assert changed_filter.value.status_code == 400


def test_signed_cursor_rejects_tampering_and_expiration(monkeypatch) -> None:
    monkeypatch.setattr(pagination.time, "time", lambda: 1_000)
    args, value = token()
    altered = value[:-1] + ("A" if value[-1] != "A" else "B")
    with pytest.raises(HTTPException) as tampered:
        pagination.decode_cursor(altered, tenant_id=args["tenant_id"], filters=args["filters"])
    assert tampered.value.status_code == 400

    monkeypatch.setattr(pagination.time, "time", lambda: 4_601)
    with pytest.raises(HTTPException) as expired:
        pagination.decode_cursor(value, tenant_id=args["tenant_id"], filters=args["filters"])
    assert expired.value.status_code == 400
