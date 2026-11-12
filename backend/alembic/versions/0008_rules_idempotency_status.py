"""New rule types, idempotent ingestion, camera rate status.

* alerts.object_class may be 'object' (debris, rule object_on_roadway)
* alerts.event_key: client-supplied idempotency key; unique per (tenant, camera) when present
* cameras.status_info: what the pipeline reports about its measured frame rate and the rules it
  can/cannot run at that rate (JSON, replaced by every heartbeat)

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = ("car", "truck", "bus", "motorcycle", "bicycle", "person")


def _clause(values: tuple[str, ...]) -> str:
    return "object_class IS NULL OR object_class IN (" + ", ".join(f"'{v}'" for v in values) + ")"


def upgrade() -> None:
    op.drop_constraint("object_class", "alerts", type_="check")
    op.create_check_constraint("object_class", "alerts", _clause((*OLD, "object")))
    op.add_column("alerts", sa.Column("event_key", sa.String(length=80), nullable=True))
    op.create_index(
        "uq_alerts_event_key",
        "alerts",
        ["tenant_id", "camera_id", "event_key"],
        unique=True,
        postgresql_where=sa.text("event_key IS NOT NULL"),
    )
    op.add_column(
        "cameras", sa.Column("status_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("cameras", "status_info")
    op.drop_index("uq_alerts_event_key", table_name="alerts")
    op.drop_column("alerts", "event_key")
    op.execute("DELETE FROM alerts WHERE object_class = 'object'")
    op.drop_constraint("object_class", "alerts", type_="check")
    op.create_check_constraint("object_class", "alerts", _clause(OLD))
