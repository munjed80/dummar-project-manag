"""Add unified locations hierarchy, contract_locations link, and location_id on complaints/tasks.

New tables:
- locations: unified location hierarchy with parent-child, type enum, coordinates, metadata
- contract_locations: many-to-many link between contracts and locations

New columns:
- complaints.location_id (FK → locations.id)
- tasks.location_id (FK → locations.id)

Revision ID: 007
Revises: 006
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    # --- locations table ---
    op.create_table(
        'locations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False, index=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('location_type', sa.String(30), nullable=False, index=True),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=True, index=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='active'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('boundary_path', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Integer(), server_default='1', index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # --- contract_locations link table ---
    op.create_table(
        'contract_locations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('contract_id', sa.Integer(), sa.ForeignKey('contracts.id'), nullable=False, index=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # --- Add location_id to complaints ---
    op.add_column('complaints', sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=True))
    op.create_index('ix_complaints_location_id', 'complaints', ['location_id'])

    # --- Add location_id to tasks ---
    op.add_column('tasks', sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=True))
    op.create_index('ix_tasks_location_id', 'tasks', ['location_id'])


def downgrade():
    op.drop_index('ix_tasks_location_id', 'tasks')
    op.drop_column('tasks', 'location_id')
    op.drop_index('ix_complaints_location_id', 'complaints')
    op.drop_column('complaints', 'location_id')
    op.drop_table('contract_locations')
    op.drop_table('locations')
