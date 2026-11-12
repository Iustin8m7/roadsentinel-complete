"""Align offline tenant indexes with ORM; additive only.

Revision ID: 0021
Revises: 0020
"""
from alembic import op
revision = '0021'
down_revision = '0020'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_recordings_tenant_id', 'recordings', ['tenant_id'])
    op.create_index('ix_analysis_runs_tenant_id', 'analysis_runs', ['tenant_id'])


def downgrade():
    op.drop_index('ix_analysis_runs_tenant_id', table_name='analysis_runs')
    op.drop_index('ix_recordings_tenant_id', table_name='recordings')
