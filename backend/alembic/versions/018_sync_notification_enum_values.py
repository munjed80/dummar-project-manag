"""Sync notificationtype enum values with NotificationType model.

Revision ID: 018
Revises: 017
Create Date: 2026-04-26
"""

from alembic import op


# revision identifiers
revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Keep existing production data and only extend the enum type.
    # IF NOT EXISTS makes this idempotent for environments that already added
    # these values manually.
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'intelligence_processing'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'location_alert'")


def downgrade() -> None:
    # PostgreSQL cannot drop individual enum values without recreating type.
    # We intentionally keep this as a no-op to avoid destructive data changes.
    pass

