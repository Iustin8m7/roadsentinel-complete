from __future__ import annotations

from sqlalchemy import select

from app.core.security import verify_password
from app.db import tenant_session
from app.models import User
from app.services.seed import seed, tenant_id_for_slug
from app.services.tenants import create_tenant

SEED_PASSWORD = "Dev-Seed-Password-2026!"


def test_existing_tenant_lookup_works_under_forced_rls() -> None:
    tenant_id = create_tenant("Lookup test", "lookup-test")
    # tenant_id_for_slug uses the app role with no tenant context; only its narrowly scoped
    # SECURITY DEFINER helper can resolve this identifier.
    assert tenant_id_for_slug("lookup-test") == tenant_id


def test_seed_repairs_partial_tenants_and_is_repeatable() -> None:
    # Simulate tenants created before account seeding completed.
    create_tenant("RoadSentinel Platform", "platform", is_platform=True)
    unit_id = create_tenant("Unit A - Highway Patrol North", "unit-a")

    first = seed(SEED_PASSWORD, users_only=True)
    second = seed(SEED_PASSWORD, users_only=True)
    assert first == second
    assert tenant_id_for_slug("unit-a") == unit_id

    with tenant_session(unit_id) as db:
        users = db.scalars(select(User).where(User.tenant_id == unit_id)).all()
        assert len(users) == 4
        operator = db.scalar(select(User).where(User.email == "operator.a@roadsentinel.local"))
        assert operator is not None
        assert verify_password(operator.password_hash, SEED_PASSWORD)
        operator.mfa_enabled = True
        db.commit()

    seed(SEED_PASSWORD, users_only=True)
    with tenant_session(unit_id) as db:
        operator = db.scalar(select(User).where(User.email == "operator.a@roadsentinel.local"))
        assert operator is not None and operator.mfa_enabled
