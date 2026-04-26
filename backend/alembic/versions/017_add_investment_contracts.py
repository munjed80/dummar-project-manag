"""Add investment_contracts table.

New table:
- investment_contracts: investor lease/investment agreement linked to an
  InvestmentProperty. Includes typed attachment slots (contract copy, terms
  booklet, IDs, ownership proof, handover report) and a JSON list of
  additional attachment paths.

Revision ID: 017
Revises: 016
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    # NOTE on PostgreSQL ENUM types: do NOT issue explicit CREATE TYPE here.
    # SQLAlchemy's sa.Enum(..., name='...') inside create_table() already
    # emits CREATE TYPE automatically on PostgreSQL.
    op.create_table(
        'investment_contracts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('contract_number', sa.String(80), nullable=False),
        sa.Column(
            'property_id',
            sa.Integer(),
            sa.ForeignKey('investment_properties.id'),
            nullable=False,
        ),
        sa.Column('investor_name', sa.String(200), nullable=False),
        sa.Column('investor_contact', sa.String(200), nullable=True),
        sa.Column(
            'investment_type',
            sa.Enum(
                'lease', 'investment', 'usufruct', 'partnership', 'other',
                name='investmenttype',
            ),
            nullable=False,
            server_default='lease',
        ),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('contract_value', sa.Numeric(15, 2), nullable=False),
        sa.Column(
            'status',
            sa.Enum(
                'active', 'near_expiry', 'expired', 'cancelled',
                name='investmentcontractstatus',
            ),
            nullable=False,
            server_default='active',
        ),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('contract_copy', sa.String(255), nullable=True),
        sa.Column('terms_booklet', sa.String(255), nullable=True),
        sa.Column('investor_id_copy', sa.String(255), nullable=True),
        sa.Column('owner_id_copy', sa.String(255), nullable=True),
        sa.Column('ownership_proof', sa.String(255), nullable=True),
        sa.Column('handover_report', sa.String(255), nullable=True),
        sa.Column('additional_attachments', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        'ix_investment_contracts_contract_number',
        'investment_contracts',
        ['contract_number'],
        unique=True,
    )
    op.create_index('ix_investment_contracts_property_id', 'investment_contracts', ['property_id'])
    op.create_index('ix_investment_contracts_status', 'investment_contracts', ['status'])
    op.create_index('ix_investment_contracts_end_date', 'investment_contracts', ['end_date'])


def downgrade():
    op.drop_index('ix_investment_contracts_end_date', 'investment_contracts')
    op.drop_index('ix_investment_contracts_status', 'investment_contracts')
    op.drop_index('ix_investment_contracts_property_id', 'investment_contracts')
    op.drop_index('ix_investment_contracts_contract_number', 'investment_contracts')
    op.drop_table('investment_contracts')
    op.execute("DROP TYPE IF EXISTS investmentcontractstatus")
    op.execute("DROP TYPE IF EXISTS investmenttype")
