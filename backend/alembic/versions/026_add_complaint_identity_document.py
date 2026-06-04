"""Add identity_document column to complaints.

Revision ID: 026
Revises: 025
Create Date: 2026-06-04

The public complaint submission form now requires a citizen-uploaded
identity document (national ID or passport image/PDF). The uploaded file
path is stored on the complaint row in a private column. The column is
intentionally never exposed via the standard ComplaintResponse schema —
admin-dashboard users retrieve it through the dedicated
``GET /complaints/{id}/identity-document`` endpoint, which is gated to
complaint-manager roles only.
"""
from alembic import op
import sqlalchemy as sa


revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "complaints",
        sa.Column("identity_document", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("complaints", "identity_document")
