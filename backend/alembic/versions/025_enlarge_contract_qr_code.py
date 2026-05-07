"""Enlarge qr_code column on contracts.

Revision ID: 025
Revises: 024
Create Date: 2026-05-06

The contract approval flow stores a base64-encoded PNG QR code in
``contracts.qr_code``. The original ``VARCHAR(255)`` is far too small —
even a tiny 100x100 QR code base64 PNG is well over a kilobyte. SQLite
silently truncated nothing because it does not enforce VARCHAR length;
PostgreSQL correctly rejects the INSERT/UPDATE with
``StringDataRightTruncation``. Switch to ``TEXT``.
"""
from alembic import op
import sqlalchemy as sa


revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "contracts",
        "qr_code",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "contracts",
        "qr_code",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
