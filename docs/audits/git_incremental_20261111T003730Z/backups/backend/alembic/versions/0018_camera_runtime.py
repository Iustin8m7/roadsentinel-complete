"""Camera runtime telemetry (Workstream D): bounded latency/memory/frozen-image metrics on the
worker status row, a source identity fingerprint on cameras (what the backend registered) and on
the worker status (what the lease holder reports it opened), and the per-camera, per-state
failure-notification throttle marks.

Additive columns only, all nullable: no new table, so no new RLS policy or grant is needed
(both tables already have ENABLE + FORCE RLS and the runtime role's grants from 0007).
Sources registered before this revision have no fingerprint until their source is set again.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "rsint_run1"
down_revision: str | None = "rsint_case1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUS_FLOATS = (
    "inference_p50_ms",
    "inference_p95_ms",
    "rss_mb",
    "frozen_signal",
    "frozen_confidence",
    "unchanged_s",
)


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '15s'")  # fail the deploy rather than queue traffic
    op.add_column("cameras", sa.Column("source_fingerprint", sa.String(64), nullable=True))
    for name in STATUS_FLOATS:
        op.add_column("camera_worker_status", sa.Column(name, sa.Float(), nullable=True))
    op.add_column(
        "camera_worker_status", sa.Column("source_fingerprint", sa.String(64), nullable=True)
    )
    op.add_column(
        "camera_worker_status",
        sa.Column("failure_notified", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '15s'")
    op.drop_column("camera_worker_status", "failure_notified")
    op.drop_column("camera_worker_status", "source_fingerprint")
    for name in reversed(STATUS_FLOATS):
        op.drop_column("camera_worker_status", name)
    op.drop_column("cameras", "source_fingerprint")
