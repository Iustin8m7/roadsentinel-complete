from __future__ import annotations

import uuid

from app.db import tenant_session
from app.models import Tenant
from app.services.keys import create_tenant_keys


def create_tenant(name: str, slug: str, *, is_platform: bool = False) -> uuid.UUID:
    """Create a tenant and its keys in a dedicated session bound to the *new* tenant id, so the
    RLS WITH CHECK clauses accept the inserts and nothing else is visible meanwhile."""
    tenant_id = uuid.uuid4()
    with tenant_session(tenant_id) as db:
        db.add(Tenant(id=tenant_id, name=name, slug=slug, is_platform=is_platform))
        db.flush()
        create_tenant_keys(db, tenant_id)
        db.commit()
    return tenant_id
