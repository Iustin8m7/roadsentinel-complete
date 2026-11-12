"""Identifier-only lookup functions get a dedicated NOLOGIN column-limited owner.

Role setup needs the explicitly configured administrator URL. No runtime role bypass.
Revision ID: 0022
Revises: 0021
"""

import os

import psycopg
from sqlalchemy.engine import make_url

from alembic import op
from app.services.lookup_roles import install_lookup_owner

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade():
    app = make_url(os.environ["RS_DATABASE_URL"])
    admin = os.environ.get("RS_ADMIN_DATABASE_URL")
    if not admin:
        raise RuntimeError(
            "0022 requires the integration-specific RS_ADMIN_DATABASE_URL for narrow lookup ownership setup"
        )
    target = make_url(admin).set(database=app.database)
    if (target.host, target.port) != (app.host, app.port):
        raise RuntimeError("Administrator and runtime database endpoints differ")
    # The admin connection must see prior schema DDL. This boundary is explicit;
    # role hardening is idempotent if Alembic version recording is interrupted.
    with (
        op.get_context().autocommit_block(),
        psycopg.connect(
            target.render_as_string(hide_password=False).replace(
                "postgresql+psycopg://", "postgresql://", 1
            )
        ) as conn,
    ):
        if conn.execute("SELECT current_database()").fetchone()[0] != app.database:
            raise RuntimeError("Lookup owner target database mismatch")
        install_lookup_owner(conn, app.username)


def downgrade():
    # Ownership hardening is intentionally retained: downgrade never broadens read privileges.
    pass
