"""Add attachment columns to investment_properties.

Revision ID: 019
Revises: 018
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa


revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("investment_properties", sa.Column("property_images", sa.Text(), nullable=True))
    op.add_column("investment_properties", sa.Column("property_documents", sa.Text(), nullable=True))
    op.add_column("investment_properties", sa.Column("owner_id_image", sa.String(length=255), nullable=True))
    op.add_column("investment_properties", sa.Column("additional_attachments", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("investment_properties", "additional_attachments")
    op.drop_column("investment_properties", "owner_id_image")
    op.drop_column("investment_properties", "property_documents")
    op.drop_column("investment_properties", "property_images")
