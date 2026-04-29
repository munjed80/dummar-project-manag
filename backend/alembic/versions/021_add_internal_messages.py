"""add internal messages

Revision ID: 021_add_internal_messages
Revises: 020_add_more_investment_contract_attachments
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "021_add_internal_messages"
down_revision = "020_add_more_investment_contract_attachments"
branch_labels = None
depends_on = None


messagethreadtype = sa.Enum("direct", "group", name="messagethreadtype")


def upgrade() -> None:
    messagethreadtype.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "message_threads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("thread_type", messagethreadtype, nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_message_threads_id"), "message_threads", ["id"], unique=False)

    op.create_table(
        "message_thread_participants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["thread_id"], ["message_threads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id", "user_id", name="uq_thread_participant"),
    )
    op.create_index(op.f("ix_message_thread_participants_id"), "message_thread_participants", ["id"], unique=False)
    op.create_index(op.f("ix_message_thread_participants_thread_id"), "message_thread_participants", ["thread_id"], unique=False)
    op.create_index(op.f("ix_message_thread_participants_user_id"), "message_thread_participants", ["user_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["thread_id"], ["message_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_messages_id"), "messages", ["id"], unique=False)
    op.create_index(op.f("ix_messages_sender_user_id"), "messages", ["sender_user_id"], unique=False)
    op.create_index(op.f("ix_messages_thread_id"), "messages", ["thread_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_thread_id"), table_name="messages")
    op.drop_index(op.f("ix_messages_sender_user_id"), table_name="messages")
    op.drop_index(op.f("ix_messages_id"), table_name="messages")
    op.drop_table("messages")

    op.drop_index(op.f("ix_message_thread_participants_user_id"), table_name="message_thread_participants")
    op.drop_index(op.f("ix_message_thread_participants_thread_id"), table_name="message_thread_participants")
    op.drop_index(op.f("ix_message_thread_participants_id"), table_name="message_thread_participants")
    op.drop_table("message_thread_participants")

    op.drop_index(op.f("ix_message_threads_id"), table_name="message_threads")
    op.drop_table("message_threads")

    messagethreadtype.drop(op.get_bind(), checkfirst=True)
