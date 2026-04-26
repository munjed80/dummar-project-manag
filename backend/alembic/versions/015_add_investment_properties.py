"""Add investment_properties table.

New table:
- investment_properties: property/asset management with type, address, area, status, owner info

Revision ID: 015
Revises: 014
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    # NOTE on PostgreSQL ENUM types: do NOT issue explicit CREATE TYPE here.
    # SQLAlchemy's sa.Enum(..., name='propertytype') inside create_table()
    # already emits CREATE TYPE automatically on PostgreSQL. Doing it twice
    # raises DuplicateObject and aborts the migration.

    op.create_table(
        'investment_properties',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            'property_type',
            sa.Enum('building', 'land', 'restaurant', 'kiosk', 'shop', 'other', name='propertytype'),
            nullable=False,
        ),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('area', sa.Numeric(10, 2), nullable=True),
        sa.Column(
            'status',
            sa.Enum('available', 'invested', 'maintenance', 'suspended', 'unfit', name='propertystatus'),
            nullable=False,
            server_default='available',
        ),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_name', sa.String(200), nullable=True),
        sa.Column('owner_info', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index('ix_investment_properties_property_type', 'investment_properties', ['property_type'])
    op.create_index('ix_investment_properties_status', 'investment_properties', ['status'])
    op.create_index('ix_investment_properties_is_active', 'investment_properties', ['is_active'])


def downgrade():
    op.drop_index('ix_investment_properties_is_active', 'investment_properties')
    op.drop_index('ix_investment_properties_status', 'investment_properties')
    op.drop_index('ix_investment_properties_property_type', 'investment_properties')
    op.drop_table('investment_properties')
    op.execute("DROP TYPE IF EXISTS propertystatus")
    op.execute("DROP TYPE IF EXISTS propertytype")
