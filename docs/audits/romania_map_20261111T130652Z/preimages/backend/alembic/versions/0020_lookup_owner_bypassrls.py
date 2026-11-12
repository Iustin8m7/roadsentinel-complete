"""Require an RLS-bypassing owner for pre-tenant lookup functions.

Revision ID: 0020
Revises: 0019
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0020"
down_revision: str | None = "rsint_case2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SECURITY DEFINER does not itself bypass forced RLS. Bootstrap must configure the
    # migration owner with BYPASSRLS; the API role remains NOBYPASSRLS and owns no tables.
    op.execute("""
        DO $$
        DECLARE owner_name text;
        BEGIN
            SELECT pg_get_userbyid(proowner) INTO owner_name
              FROM pg_proc WHERE oid = 'rs_tenant_id_by_slug(text)'::regprocedure;
            IF owner_name IS NULL OR NOT EXISTS (
                SELECT 1 FROM pg_roles WHERE rolname = owner_name AND rolbypassrls
            ) THEN
                RAISE EXCEPTION 'SECURITY DEFINER lookup owner must have BYPASSRLS; rerun app.cli bootstrap as database administrator';
            END IF;
        END $$
    """)
    # Make the owner requirement explicit on every pre-tenant lookup, including auth helpers.
    op.execute("""
        DO $$
        DECLARE fn record;
        BEGIN
            FOR fn IN SELECT p.oid::regprocedure AS signature, r.rolbypassrls
                FROM pg_proc p JOIN pg_roles r ON r.oid = p.proowner
                WHERE p.proname IN (
                    'rs_tenant_id_by_slug', 'rs_resource_tenant', 'rs_auth_find_user',
                    'rs_auth_find_refresh_tenant', 'rs_auth_find_invitation_tenant',
                    'rs_platform_tenant'
                )
            LOOP
                IF NOT fn.rolbypassrls THEN
                    RAISE EXCEPTION 'lookup function % is owned by a role without BYPASSRLS', fn.signature;
                END IF;
            END LOOP;
        END $$
    """)


def downgrade() -> None:
    pass
