"""Account recovery: four-eyes reset requests and single-use reset tokens.

* approval_kind gains 'account_reset'; approval_requests.params carries {"reset_mfa": bool}
* invitations get kind ('invite' | 'reset'), user_id (the account a reset token belongs to) and reset_mfa.
  A reset token is an invitation row of kind 'reset': same hashing, expiry, single use, RLS and
  token-lookup function.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE approval_kind ADD VALUE IF NOT EXISTS 'account_reset'")
    op.add_column(
        "approval_requests",
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "invitations",
        sa.Column("kind", sa.String(length=10), nullable=False, server_default="invite"),
    )
    op.add_column("invitations", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "invitations",
        sa.Column("reset_mfa", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_check_constraint("kind", "invitations", "kind IN ('invite', 'reset')")
    op.create_foreign_key(
        "fk_invitations_user_id_users",
        "invitations",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_invitations_user_id_users", "invitations", type_="foreignkey")
    op.drop_constraint("kind", "invitations", type_="check")
    op.drop_column("invitations", "reset_mfa")
    op.drop_column("invitations", "user_id")
    op.drop_column("invitations", "kind")
    op.drop_column("approval_requests", "params")
    # Postgres cannot drop an enum value; 'account_reset' stays in the type (harmless).
