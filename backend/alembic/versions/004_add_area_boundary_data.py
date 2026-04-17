"""Add boundary_polygon and color columns to areas table.

Stores area boundary data in the database instead of hardcoded dict.
boundary_polygon stores the polygon as JSON array of [lat, lng] pairs.
color stores the hex color for map display.

Revision ID: 004
Revises: 003
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('areas', sa.Column('boundary_polygon', sa.Text(), nullable=True))
    op.add_column('areas', sa.Column('color', sa.String(20), nullable=True))


def downgrade():
    op.drop_column('areas', 'color')
    op.drop_column('areas', 'boundary_polygon')
