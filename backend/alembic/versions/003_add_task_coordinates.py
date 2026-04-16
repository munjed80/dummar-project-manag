"""Add latitude/longitude to tasks for GIS map display.

Revision ID: 003
Revises: 002
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tasks', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('tasks', sa.Column('longitude', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('tasks', 'longitude')
    op.drop_column('tasks', 'latitude')
