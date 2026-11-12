"""Database engine, sessions and the per-transaction tenant context used by Row-Level Security.

Every tenant-scoped table has an RLS policy comparing ``tenant_id`` to the transaction-local
setting ``app.tenant_id``. The setting is applied with ``set_config(..., is_local => true)``
(equivalent to ``SET LOCAL``) at the start of *every* transaction of a session that carries a
tenant, so a commit inside a request can never leave later queries unscoped. A session without
a tenant sees zero rows (fail closed).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, SessionTransaction, sessionmaker

from app.config import get_settings

TENANT_KEY = "tenant_id"


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url.get_secret_value()
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=10)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=True)


@event.listens_for(Session, "after_begin")
def _apply_tenant_context(
    session: Session, transaction: SessionTransaction, connection: object
) -> None:
    tenant_id = session.info.get(TENANT_KEY)
    if tenant_id is not None:
        connection.execute(  # type: ignore[attr-defined]
            text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)}
        )


def set_tenant(session: Session, tenant_id: uuid.UUID) -> None:
    """Bind the session to a tenant for the current and all future transactions."""
    session.info[TENANT_KEY] = tenant_id
    if session.in_transaction():
        session.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)}
        )


def current_tenant(session: Session) -> uuid.UUID | None:
    return session.info.get(TENANT_KEY)


@contextmanager
def tenant_session(tenant_id: uuid.UUID | None = None) -> Iterator[Session]:
    """A standalone session (outside the request cycle), optionally bound to a tenant."""
    session = get_sessionmaker()()
    try:
        if tenant_id is not None:
            set_tenant(session, tenant_id)
        yield session
    finally:
        session.close()
