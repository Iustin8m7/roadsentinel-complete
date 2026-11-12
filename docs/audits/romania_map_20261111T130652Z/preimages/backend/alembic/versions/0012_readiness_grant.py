"""Let the runtime role read alembic_version so /api/ready can tell whether the schema is migrated.

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-05
"""

import os
from collections.abc import Sequence

from sqlalchemy.engine import make_url

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _app_role() -> str:
    url = os.environ.get("RS_DATABASE_URL")
    name = (make_url(url).username if url else None) or "rs_app"
    if not name.replace("_", "").isalnum():
        raise ValueError("unexpected app role name")
    return name


def upgrade() -> None:
    op.execute(f"GRANT SELECT ON alembic_version TO {_app_role()}")


def downgrade() -> None:
    op.execute(f"REVOKE SELECT ON alembic_version FROM {_app_role()}")  # noqa: S608
