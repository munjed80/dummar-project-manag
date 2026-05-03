"""Add CORRUPTION to complainttype enum.

Revision ID: 024
Revises: 023
Create Date: 2026-05-02

A new sensitive complaint category for citizen-reported corruption was
added to the public complaint form. The PG enum needs the new label so
new submissions can persist. Visibility/scoping of CORRUPTION rows is
handled in the API layer (see app.core.permissions).

On SQLite (used by tests) enums are plain VARCHAR + CHECK constraint,
and the test conftest re-creates schema from current SQLAlchemy
metadata, so this migration is a Postgres-only no-op when running under
SQLite.
"""
from alembic import op


# revision identifiers
revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return
    op.execute("ALTER TYPE complainttype ADD VALUE IF NOT EXISTS 'CORRUPTION'")


def downgrade():
    # Removing a value from a PG enum is not supported without recreating
    # the type. We intentionally leave the value in place on downgrade
    # rather than risk data loss for existing complaints.
    pass
