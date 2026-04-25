"""Add execution_logs table.

Revision ID: 011
Revises: 010
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


# NOTE: status / action_type are stored as plain strings (not Postgres ENUMs)
# so new outcomes can be added without an ALTER TYPE migration.


def upgrade():
    op.create_table(
        'execution_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('action_type', sa.String(50), nullable=False, index=True),
        sa.Column('action_name', sa.String(200), nullable=False, index=True),
        sa.Column('status', sa.String(20), nullable=False, index=True),
        sa.Column('entity_type', sa.String(50), nullable=True, index=True),
        sa.Column('entity_id', sa.Integer(), nullable=True, index=True),
        sa.Column(
            'user_id',
            sa.Integer(),
            sa.ForeignKey('users.id', name='fk_execution_logs_user_id_users'),
            nullable=True,
            index=True,
        ),
        sa.Column('payload', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column(
            'started_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            index=True,
        ),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            index=True,
        ),
    )

    # Composite index to accelerate the common dashboard query
    # "show me failed actions of type X in the last hour".
    op.create_index(
        'ix_execution_logs_action_type_status_created_at',
        'execution_logs',
        ['action_type', 'status', 'created_at'],
    )


def downgrade():
    op.drop_index(
        'ix_execution_logs_action_type_status_created_at',
        table_name='execution_logs',
    )
    op.drop_table('execution_logs')
