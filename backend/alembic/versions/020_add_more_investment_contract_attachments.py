"""Add handover images and financial docs fields to investment_contracts.

Revision ID: 020
Revises: 019
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa


revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("investment_contracts", sa.Column("handover_property_images", sa.Text(), nullable=True))
    op.add_column("investment_contracts", sa.Column("financial_documents", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("investment_contracts", "financial_documents")
    op.drop_column("investment_contracts", "handover_property_images")
