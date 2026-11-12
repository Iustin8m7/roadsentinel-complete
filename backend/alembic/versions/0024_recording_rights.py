"""Persist scoped rights declarations for uploaded recordings.

Revision ID: 0024
Revises: 0023
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("recordings", sa.Column("rights_context", JSONB(), nullable=True))
    op.add_column(
        "recordings",
        sa.Column("rights_revision", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_check_constraint("recording_rights_revision_nonnegative", "recordings", "rights_revision >= 0")


def downgrade():
    op.drop_constraint("recording_rights_revision_nonnegative", "recordings", type_="check")
    op.drop_column("recordings", "rights_revision")
    op.drop_column("recordings", "rights_context")
