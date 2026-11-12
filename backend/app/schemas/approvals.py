from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import ApprovalKind, ApprovalStatus


class ApprovalIn(BaseModel):
    kind: ApprovalKind = ApprovalKind.unblur
    evidence_id: uuid.UUID
    justification: str = Field(min_length=20, max_length=2000)
    case_reference: str = Field(min_length=3, max_length=100)

    @field_validator("kind")
    @classmethod
    def _evidence_kinds_only(cls, v: ApprovalKind) -> ApprovalKind:
        if v not in (ApprovalKind.unblur, ApprovalKind.export):
            raise ValueError("this endpoint only creates unblur / export requests")
        return v


class ApprovalDecisionIn(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: ApprovalKind
    resource_type: str
    resource_id: uuid.UUID
    requester_id: uuid.UUID
    justification: str
    case_reference: str
    status: ApprovalStatus
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    decision_note: str | None
    grant_expires_at: datetime | None
    grant_active: bool = False
    created_at: datetime
