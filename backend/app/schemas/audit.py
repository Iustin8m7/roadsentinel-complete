from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    ts: datetime
    actor_id: uuid.UUID | None
    action: str
    resource_type: str | None
    resource_id: str | None
    ip: str | None
    details: dict[str, Any]
    prev_hash: str
    entry_hash: str


class AuditVerifyOut(BaseModel):
    ok: bool
    checked: int
    first_broken_seq: int | None
    reason: str | None
    head_hash: str | None
