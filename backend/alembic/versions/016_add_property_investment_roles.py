"""Add property_manager and investment_manager to userrole enum.

Revision ID: 016
Revises: 015
Create Date: 2026-04-26

The system gained two new internal roles for the investment properties
module:
  - PROPERTY_MANAGER (مسؤول الأصول): full CRUD on investment properties.
  - INVESTMENT_MANAGER (مسؤول الاستثمار): view-only on properties for now;
    will manage investment contracts in a later phase.

Existing rows keep their roles; we only extend the PG enum with the new
labels so new accounts can persist.

On SQLite (used by tests) enums are plain VARCHAR + CHECK constraint, and
the test conftest re-creates schema from current SQLAlchemy metadata, so
this migration is a Postgres-only no-op when running under SQLite.
"""
from alembic import op


# revision identifiers
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return
    # ALTER TYPE ... ADD VALUE must run outside a transaction in older PG
    # versions; modern (>=12) supports it inside, which alembic uses.
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'PROPERTY_MANAGER'")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'INVESTMENT_MANAGER'")


def downgrade():
    # Removing a value from a PG enum is not supported without recreating
    # the type. We intentionally leave the values in place on downgrade
    # rather than risk data loss for existing user accounts.
    pass
