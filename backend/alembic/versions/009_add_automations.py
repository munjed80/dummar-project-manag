"""Add automations table.

Revision ID: 009
Revises: 008
Create Date: 2026-04-24
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # NOTE on PostgreSQL ENUM types: SQLAlchemy's `sa.Enum(..., name='...')`
    # inside create_table() already emits CREATE TYPE on PostgreSQL. Do NOT
    # `op.execute("CREATE TYPE ...")` here or the migration will fail with
    # DuplicateObject. See migrations/008 for the same pattern.
    op.create_table(
        'automations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'trigger',
            sa.Enum(
                'complaint_created',
                'complaint_status_changed',
                'task_created',
                'task_status_changed',
                name='automationtrigger',
            ),
            nullable=False,
        ),
        sa.Column('conditions', sa.Text(), nullable=True),
        sa.Column('actions', sa.Text(), nullable=False),
        # Boolean default: use sa.text('true') NOT '1' (PG would reject '1').
        sa.Column(
            'enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
        ),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'run_count',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
        ),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column(
            'created_by_id',
            sa.Integer(),
            sa.ForeignKey('users.id'),
            nullable=True,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f('ix_automations_trigger'), 'automations', ['trigger'], unique=False
    )


def downgrade():
    op.drop_index(op.f('ix_automations_trigger'), table_name='automations')
    op.drop_table('automations')
    # Drop the enum type on PostgreSQL.
    op.execute("DROP TYPE IF EXISTS automationtrigger")
