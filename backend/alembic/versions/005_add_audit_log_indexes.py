"""Add indexes to audit_logs for query performance.

Revision ID: 005
Revises: 004
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_user_entity', 'audit_logs', ['user_id', 'entity_type'])


def downgrade():
    op.drop_index('ix_audit_logs_user_entity', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
