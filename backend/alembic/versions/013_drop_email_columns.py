"""Drop email-related columns (users.email, teams.contact_email).

Revision ID: 013
Revises: 012
Create Date: 2026-04-25

The system has no email-sending capability and never did rely on email
addresses operationally. The optional contact-email columns are removed
so the schema cannot be confused for an email-aware system.
"""
from alembic import op


# revision identifiers
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    # users.email — drop the unique index first, then the column.
    with op.batch_alter_table('users') as batch_op:
        try:
            batch_op.drop_index('ix_users_email')
        except Exception:
            # Index name may differ across historical environments; ignore.
            pass
        batch_op.drop_column('email')

    # teams.contact_email
    with op.batch_alter_table('teams') as batch_op:
        batch_op.drop_column('contact_email')


def downgrade():
    import sqlalchemy as sa

    with op.batch_alter_table('teams') as batch_op:
        batch_op.add_column(sa.Column('contact_email', sa.String(200), nullable=True))

    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(100), nullable=True))
        batch_op.create_index('ix_users_email', ['email'], unique=True)
