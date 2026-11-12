"""Evidence integrity: record whether a distinct original exists.

Pipeline evidence was stored once and exposed as both "original" and "redacted". Rows where
both paths point at the same file have no distinct original: has_original=false.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "evidence",
        sa.Column("has_original", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.execute("UPDATE evidence SET has_original = (original_path <> redacted_path)")
    op.drop_constraint("redaction", "evidence", type_="check")
    op.create_check_constraint(
        "redaction", "evidence", "redaction IN ('full', 'heads_only', 'off', 'unknown')"
    )


def downgrade() -> None:
    op.execute("UPDATE evidence SET redaction = 'heads_only' WHERE redaction IN ('off', 'unknown')")
    op.drop_constraint("redaction", "evidence", type_="check")
    op.create_check_constraint("redaction", "evidence", "redaction IN ('full', 'heads_only')")
    op.drop_column("evidence", "has_original")
