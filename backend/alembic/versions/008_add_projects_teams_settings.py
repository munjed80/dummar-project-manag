"""Add projects, teams, app_settings tables and foreign keys.

New tables:
- projects: project management with status, dates, location/contract links
- teams: execution teams/units with type, contacts, activity status
- app_settings: key-value store for application settings

New columns:
- tasks.team_id (FK → teams.id)
- tasks.project_id (FK → projects.id)
- contracts.project_id (FK → projects.id)
- complaints.project_id (FK → projects.id)

Revision ID: 008
Revises: 007
Create Date: 2026-04-23
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    # NOTE on PostgreSQL ENUM types: we intentionally do NOT issue an explicit
    # `CREATE TYPE projectstatus ...` / `CREATE TYPE teamtype ...` here.
    # SQLAlchemy's `sa.Enum(..., name='projectstatus')` inside create_table()
    # already emits `CREATE TYPE` automatically on PostgreSQL. Doing it twice
    # raises `DuplicateObject: type "projectstatus" already exists` and aborts
    # the whole migration (which previously caused the backend container to
    # exit 1 in entrypoint.sh and never become healthy).

    # --- projects table ---
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('code', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('planned', 'active', 'on_hold', 'completed', 'cancelled', name='projectstatus'), nullable=False, server_default='active'),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=True, index=True),
        sa.Column('contract_id', sa.Integer(), sa.ForeignKey('contracts.id'), nullable=True, index=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # --- teams table ---
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('team_type', sa.Enum('internal_team', 'contractor', 'field_crew', 'supervision_unit', name='teamtype'), nullable=False, server_default='internal_team'),
        sa.Column('contact_name', sa.String(200), nullable=True),
        sa.Column('contact_phone', sa.String(50), nullable=True),
        sa.Column('contact_email', sa.String(200), nullable=True),
        # Note: PostgreSQL rejects '1' as a Boolean literal at CREATE TABLE
        # time (invalid input syntax for type boolean: "1"). Use sa.text('true')
        # so the DDL is portable across PostgreSQL (production) and SQLite
        # (tests). This matches the pattern used in 006 for `is_resolved`.
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), index=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=True, index=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=True, index=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # --- app_settings table ---
    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('key', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('value_type', sa.String(20), server_default='string'),
        sa.Column('category', sa.String(50), server_default='general', index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # --- Add team_id to tasks ---
    op.add_column('tasks', sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=True))
    op.create_index('ix_tasks_team_id', 'tasks', ['team_id'])

    # --- Add project_id to tasks ---
    op.add_column('tasks', sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=True))
    op.create_index('ix_tasks_project_id', 'tasks', ['project_id'])

    # --- Add project_id to contracts ---
    op.add_column('contracts', sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=True))
    op.create_index('ix_contracts_project_id', 'contracts', ['project_id'])

    # --- Add project_id to complaints ---
    op.add_column('complaints', sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=True))
    op.create_index('ix_complaints_project_id', 'complaints', ['project_id'])


def downgrade():
    # Drop indexes and columns
    op.drop_index('ix_complaints_project_id', 'complaints')
    op.drop_column('complaints', 'project_id')
    
    op.drop_index('ix_contracts_project_id', 'contracts')
    op.drop_column('contracts', 'project_id')
    
    op.drop_index('ix_tasks_project_id', 'tasks')
    op.drop_column('tasks', 'project_id')
    
    op.drop_index('ix_tasks_team_id', 'tasks')
    op.drop_column('tasks', 'team_id')
    
    # Drop tables
    op.drop_table('app_settings')
    op.drop_table('teams')
    op.drop_table('projects')

    # Drop enum types — SQLAlchemy does NOT auto-drop ENUM types when the
    # owning table is dropped on PostgreSQL, so we must do it explicitly to
    # keep `downgrade` symmetric with `upgrade`.
    op.execute("DROP TYPE IF EXISTS teamtype")
    op.execute("DROP TYPE IF EXISTS projectstatus")
