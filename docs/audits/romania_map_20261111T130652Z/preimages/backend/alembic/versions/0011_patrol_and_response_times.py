"""Patrol workflow status and first-view timestamp (for response-time statistics).

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("patrol_status", sa.String(length=12), nullable=True))
    op.add_column(
        "alerts", sa.Column("patrol_status_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("alerts", sa.Column("first_viewed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "patrol_status",
        "alerts",
        "patrol_status IS NULL OR patrol_status IN ('assigned', 'en_route', 'on_scene', 'done')",
    )


def downgrade() -> None:
    op.drop_constraint("patrol_status", "alerts", type_="check")
    for col in ("first_viewed_at", "patrol_status_at", "patrol_status"):
        op.drop_column("alerts", col)
