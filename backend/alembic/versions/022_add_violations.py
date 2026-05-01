"""Add violations table.

New table:
- violations: independent module for tracking municipal violations
  (building, occupancy, hygiene, etc.) with severity, status workflow,
  optional links to a complaint/task that triggered the violation, and
  organizational scoping (municipality/district).

Revision ID: 022
Revises: 021
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NOTE on PostgreSQL ENUM types: do NOT issue explicit CREATE TYPE here.
    # SQLAlchemy's sa.Enum(..., name='...') inside create_table() already
    # emits CREATE TYPE automatically on PostgreSQL. Doing it twice raises
    # DuplicateObject and aborts the migration.

    op.create_table(
        "violations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("violation_number", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "violation_type",
            sa.Enum(
                "building",
                "occupancy",
                "market",
                "hygiene",
                "road",
                "environment",
                "public_property",
                "other",
                name="violationtype",
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "low",
                "medium",
                "high",
                "critical",
                name="violationseverity",
            ),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "new",
                "under_review",
                "inspection_required",
                "violation_confirmed",
                "notice_sent",
                "fined",
                "resolved",
                "rejected",
                "referred_to_legal",
                name="violationstatus",
            ),
            nullable=False,
            server_default="new",
        ),
        sa.Column(
            "municipality_id",
            sa.Integer(),
            sa.ForeignKey("organization_units.id"),
            nullable=True,
        ),
        sa.Column(
            "district_id",
            sa.Integer(),
            sa.ForeignKey("organization_units.id"),
            nullable=True,
        ),
        sa.Column(
            "org_unit_id",
            sa.Integer(),
            sa.ForeignKey("organization_units.id"),
            nullable=True,
        ),
        sa.Column(
            "reported_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "assigned_to_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "related_complaint_id",
            sa.Integer(),
            sa.ForeignKey("complaints.id"),
            nullable=True,
        ),
        sa.Column(
            "related_task_id",
            sa.Integer(),
            sa.ForeignKey("tasks.id"),
            nullable=True,
        ),
        sa.Column("location_text", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("legal_reference", sa.String(length=255), nullable=True),
        sa.Column("fine_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("deadline_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("violation_number", name="uq_violations_violation_number"),
    )

    op.create_index("ix_violations_violation_number", "violations", ["violation_number"])
    op.create_index("ix_violations_violation_type", "violations", ["violation_type"])
    op.create_index("ix_violations_severity", "violations", ["severity"])
    op.create_index("ix_violations_status", "violations", ["status"])
    op.create_index("ix_violations_municipality_id", "violations", ["municipality_id"])
    op.create_index("ix_violations_district_id", "violations", ["district_id"])
    op.create_index("ix_violations_org_unit_id", "violations", ["org_unit_id"])
    op.create_index("ix_violations_reported_by_user_id", "violations", ["reported_by_user_id"])
    op.create_index("ix_violations_assigned_to_user_id", "violations", ["assigned_to_user_id"])
    op.create_index("ix_violations_related_complaint_id", "violations", ["related_complaint_id"])
    op.create_index("ix_violations_related_task_id", "violations", ["related_task_id"])


def downgrade() -> None:
    op.drop_index("ix_violations_related_task_id", "violations")
    op.drop_index("ix_violations_related_complaint_id", "violations")
    op.drop_index("ix_violations_assigned_to_user_id", "violations")
    op.drop_index("ix_violations_reported_by_user_id", "violations")
    op.drop_index("ix_violations_org_unit_id", "violations")
    op.drop_index("ix_violations_district_id", "violations")
    op.drop_index("ix_violations_municipality_id", "violations")
    op.drop_index("ix_violations_status", "violations")
    op.drop_index("ix_violations_severity", "violations")
    op.drop_index("ix_violations_violation_type", "violations")
    op.drop_index("ix_violations_violation_number", "violations")
    op.drop_table("violations")
    op.execute("DROP TYPE IF EXISTS violationstatus")
    op.execute("DROP TYPE IF EXISTS violationseverity")
    op.execute("DROP TYPE IF EXISTS violationtype")
