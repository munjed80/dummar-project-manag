"""Add HEATING_NETWORK to complainttype enum.

Revision ID: 014
Revises: 013
Create Date: 2026-04-26

The system gained a new resident-facing request type for heating-network
maintenance. Existing rows keep their values; we only extend the PG enum
with the new label so new submissions can persist.

On SQLite (used by tests) enums are plain VARCHAR + CHECK constraint, and
the test conftest re-creates schema from current SQLAlchemy metadata, so
this migration is a Postgres-only no-op when running under SQLite.
"""
from alembic import op


# revision identifiers
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return
    # ALTER TYPE ... ADD VALUE must run outside a transaction in older PG
    # versions; modern (>=12) supports it inside, which alembic uses.
    op.execute("ALTER TYPE complainttype ADD VALUE IF NOT EXISTS 'HEATING_NETWORK'")


def downgrade():
    # Removing a value from a PG enum is not supported without recreating
    # the type. We intentionally leave the value in place on downgrade
    # rather than risk data loss for existing complaints.
    pass
