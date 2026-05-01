"""Add context fields to message_threads.

Phase 2 of internal messages: allow a thread to be linked to a specific
entity (e.g. a complaint). All three columns are nullable so existing
threads are unaffected.

Revision ID: 023
Revises: 022
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "message_threads",
        sa.Column("context_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "message_threads",
        sa.Column("context_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "message_threads",
        sa.Column("context_title", sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f("ix_message_threads_context_type"),
        "message_threads",
        ["context_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_message_threads_context_id"),
        "message_threads",
        ["context_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_message_threads_context_id"), table_name="message_threads")
    op.drop_index(op.f("ix_message_threads_context_type"), table_name="message_threads")
    op.drop_column("message_threads", "context_title")
    op.drop_column("message_threads", "context_id")
    op.drop_column("message_threads", "context_type")
