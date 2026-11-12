"""Persist structured vehicle-observation artifact metadata.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("analysis_runs", sa.Column("observation_storage_key", sa.String(300)))
    op.add_column("analysis_runs", sa.Column("observation_sha256", sa.String(64)))
    op.add_column("analysis_runs", sa.Column("observation_size_bytes", sa.BigInteger()))
    op.add_column(
        "analysis_runs",
        sa.Column("observation_count", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column("analysis_runs", sa.Column("observation_schema_version", sa.Integer()))
    op.add_column(
        "analysis_runs",
        sa.Column("observations_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_check_constraint(
        "analysis_runs_observation_metadata_consistent",
        "analysis_runs",
        "(observations_complete = false) OR "
        "(status = 'completed' AND observation_storage_key IS NOT NULL "
        "AND observation_sha256 IS NOT NULL AND observation_schema_version = 1)",
    )
    op.create_check_constraint(
        "analysis_runs_observation_size_bound",
        "analysis_runs",
        "observation_count >= 0 AND "
        "(observation_size_bytes IS NULL OR observation_size_bytes BETWEEN 1 AND 134217728)",
    )


def downgrade() -> None:
    op.drop_constraint("analysis_runs_observation_size_bound", "analysis_runs")
    op.drop_constraint("analysis_runs_observation_metadata_consistent", "analysis_runs")
    op.drop_column("analysis_runs", "observations_complete")
    op.drop_column("analysis_runs", "observation_schema_version")
    op.drop_column("analysis_runs", "observation_count")
    op.drop_column("analysis_runs", "observation_size_bytes")
    op.drop_column("analysis_runs", "observation_sha256")
    op.drop_column("analysis_runs", "observation_storage_key")
