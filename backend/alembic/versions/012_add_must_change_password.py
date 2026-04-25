"""Add must_change_password flag to users.

Revision ID: 012
Revises: 011
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column(
            'must_change_password',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )


def downgrade():
    op.drop_column('users', 'must_change_password')
