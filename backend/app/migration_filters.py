"""Alembic autogenerate filter (shared by alembic/env.py and the schema-drift test).

Security constraints created in hand-written migrations (composite tenant FKs and the
(tenant_id, id) unique keys they reference) are not declared on the models. Without this
filter, autogenerate would propose DROPPING them. Never remove it.
"""

from __future__ import annotations

from typing import Any

PROTECTED_PREFIXES = ("uq_", "fk_")
PROTECTED_MARKERS = ("_tenant_id_id", "_tenant_")


def include_object(
    obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    return not (
        reflected
        and compare_to is None
        and type_ in ("unique_constraint", "foreign_key_constraint")
        and name
        and name.startswith(PROTECTED_PREFIXES)
        and any(m in name for m in PROTECTED_MARKERS)
    )
