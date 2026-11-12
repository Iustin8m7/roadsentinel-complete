"""Service accounts for signed pipeline ingestion; tighter grants on tenants.

* ``service_accounts`` / ``service_keys`` / ``ingest_nonces`` are tenant-scoped with forced RLS.
* ``rs_service_key_tenant(key_id)`` (SECURITY DEFINER) returns only the tenant of a key, so a
  signed request can be bound to its tenant before any tenant context exists.
* The runtime role loses UPDATE/DELETE on ``tenants`` (nothing in the API needs it; it would
  let a bug flip ``is_platform``).

NOTE: autogenerate does not know the composite tenant FKs created in 0002 (they are not on the
models) and proposes dropping them. Never accept that; this file is written by hand.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-17
"""

import os
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TABLES = ("service_accounts", "service_keys", "ingest_nonces")
BASE_PROBE_TABLES = (
    "users",
    "cameras",
    "alerts",
    "evidence",
    "approval_requests",
    "user_sessions",
    "invitations",
)


def _resource_tenant_fn(tables: tuple[str, ...]) -> str:
    allowed = ", ".join(f"'{t}'" for t in tables)
    return f"""
        CREATE OR REPLACE FUNCTION rs_resource_tenant(p_table text, p_id uuid) RETURNS uuid
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
        DECLARE result uuid;
        BEGIN
            IF p_table NOT IN ({allowed}) THEN
                RAISE EXCEPTION 'table not allowed';
            END IF;
            EXECUTE format('SELECT tenant_id FROM %I WHERE id = $1', p_table)
                INTO result USING p_id;
            RETURN result;
        END $$
    """  # noqa: S608 - fixed allow-list, no user input


def _app_role() -> str:
    url = os.environ.get("RS_DATABASE_URL")
    name = (make_url(url).username if url else None) or "rs_app"
    if not name.replace("_", "").isalnum():
        raise ValueError("unexpected app role name")
    return name


def upgrade() -> None:
    app = _app_role()
    op.create_table(
        "service_accounts",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("camera_ids", postgresql.ARRAY(sa.UUID()), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_service_accounts_created_by_users"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_service_accounts_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_service_accounts"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_service_accounts_tenant_id_id"),
    )
    op.create_index("ix_service_accounts_tenant_id", "service_accounts", ["tenant_id"])
    op.create_table(
        "service_keys",
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("key_id", sa.String(length=40), nullable=False),
        sa.Column("secret_enc", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "account_id"],
            ["service_accounts.tenant_id", "service_accounts.id"],
            name="fk_service_keys_tenant_account",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_service_keys_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_service_keys"),
        sa.UniqueConstraint("key_id", name="uq_service_keys_key_id"),
    )
    op.create_index("ix_service_keys_account_id", "service_keys", ["account_id"])
    op.create_index("ix_service_keys_tenant_id", "service_keys", ["tenant_id"])
    op.create_table(
        "ingest_nonces",
        sa.Column("key_id", sa.String(length=40), nullable=False),
        sa.Column("nonce", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_ingest_nonces_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("key_id", "nonce", name="pk_ingest_nonces"),
    )
    op.create_index("ix_ingest_nonces_expires_at", "ingest_nonces", ["expires_at"])
    op.create_index("ix_ingest_nonces_tenant_id", "ingest_nonces", ["tenant_id"])

    for table in NEW_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = rs_current_tenant())
            WITH CHECK (tenant_id = rs_current_tenant())
        """)
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON service_accounts, service_keys TO {app}")
    op.execute(f"GRANT SELECT, INSERT, DELETE ON ingest_nonces TO {app}")

    op.execute("""
        CREATE FUNCTION rs_service_key_tenant(p_key_id text) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$ SELECT k.tenant_id FROM service_keys k WHERE k.key_id = p_key_id $$
    """)
    op.execute("REVOKE ALL ON FUNCTION rs_service_key_tenant(text) FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION rs_service_key_tenant(text) TO {app}")

    # Cross-tenant probe detection also covers service accounts (same fixed allow-list).
    op.execute(_resource_tenant_fn((*BASE_PROBE_TABLES, "service_accounts")))

    # Least privilege on tenants: the API only ever reads and creates tenant rows.
    op.execute(f"REVOKE UPDATE, DELETE ON tenants FROM {app}")


def downgrade() -> None:
    app = _app_role()
    op.execute(f"GRANT UPDATE, DELETE ON tenants TO {app}")
    op.execute("DROP FUNCTION IF EXISTS rs_service_key_tenant(text)")
    op.execute(_resource_tenant_fn(BASE_PROBE_TABLES))
    op.drop_table("ingest_nonces")
    op.drop_table("service_keys")
    op.drop_table("service_accounts")
