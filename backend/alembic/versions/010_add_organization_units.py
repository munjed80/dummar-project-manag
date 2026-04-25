"""Add organization_units table and org_unit_id columns.

Revision ID: 010
Revises: 009
Create Date: 2026-04-24
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


# NOTE on PostgreSQL ENUM types: SQLAlchemy's `sa.Enum(..., name='...')` inside
# create_table() already emits CREATE TYPE on PostgreSQL. Do NOT
# `op.execute("CREATE TYPE ...")` here or the migration will fail with
# DuplicateObject. Boolean defaults must use sa.text('true')/('false'); the
# string '1' is rejected by PG.


def upgrade():
    op.create_table(
        'organization_units',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False, index=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column(
            'level',
            sa.Enum(
                'governorate',
                'municipality',
                'district',
                name='orglevel',
            ),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'parent_id',
            sa.Integer(),
            sa.ForeignKey('organization_units.id'),
            nullable=True,
            index=True,
        ),
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Add nullable org_unit_id columns to scoped resources.
    for table in ('users', 'complaints', 'tasks', 'contracts', 'projects'):
        op.add_column(
            table,
            sa.Column('org_unit_id', sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            f'fk_{table}_org_unit_id_organization_units',
            table,
            'organization_units',
            ['org_unit_id'],
            ['id'],
        )
        op.create_index(
            f'ix_{table}_org_unit_id', table, ['org_unit_id'], unique=False
        )


def downgrade():
    for table in ('users', 'complaints', 'tasks', 'contracts', 'projects'):
        op.drop_index(f'ix_{table}_org_unit_id', table_name=table)
        op.drop_constraint(
            f'fk_{table}_org_unit_id_organization_units',
            table,
            type_='foreignkey',
        )
        op.drop_column(table, 'org_unit_id')

    op.drop_table('organization_units')
    # Drop the enum type on PostgreSQL.
    op.execute("DROP TYPE IF EXISTS orglevel")
