"""Add contract intelligence tables"""
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # Create contract_documents table
    op.create_table(
        'contract_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_filename', sa.String(length=500), nullable=False),
        sa.Column('stored_path', sa.String(length=500), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('processing_status', sa.Enum('QUEUED', 'PROCESSING', 'OCR_COMPLETE', 'EXTRACTED', 'REVIEW', 'APPROVED', 'REJECTED', 'FAILED', name='documentprocessingstatus'), nullable=False),
        sa.Column('ocr_text', sa.Text(), nullable=True),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('ocr_engine', sa.String(length=100), nullable=True),
        sa.Column('ocr_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extracted_fields', sa.Text(), nullable=True),
        sa.Column('extraction_confidence', sa.Float(), nullable=True),
        sa.Column('extraction_notes', sa.Text(), nullable=True),
        sa.Column('suggested_type', sa.String(length=50), nullable=True),
        sa.Column('classification_confidence', sa.Float(), nullable=True),
        sa.Column('classification_reason', sa.Text(), nullable=True),
        sa.Column('auto_summary', sa.Text(), nullable=True),
        sa.Column('edited_summary', sa.Text(), nullable=True),
        sa.Column('contract_id', sa.Integer(), nullable=True),
        sa.Column('import_batch_id', sa.String(length=100), nullable=True),
        sa.Column('import_source', sa.String(length=50), nullable=True),
        sa.Column('uploaded_by_id', sa.Integer(), nullable=False),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contract_documents_id'), 'contract_documents', ['id'], unique=False)
    op.create_index('ix_contract_documents_batch', 'contract_documents', ['import_batch_id'], unique=False)
    op.create_index('ix_contract_documents_status', 'contract_documents', ['processing_status'], unique=False)

    # Create contract_risk_flags table
    op.create_table(
        'contract_risk_flags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('contract_id', sa.Integer(), nullable=True),
        sa.Column('risk_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='riskseverity'), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), default=False),
        sa.Column('resolved_by_id', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['contract_documents.id']),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contract_risk_flags_id'), 'contract_risk_flags', ['id'], unique=False)

    # Create contract_duplicates table
    op.create_table(
        'contract_duplicates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('contract_id_a', sa.Integer(), nullable=True),
        sa.Column('contract_id_b', sa.Integer(), nullable=True),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('match_reasons', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'CONFIRMED_SAME', 'CONFIRMED_DIFFERENT', 'REVIEW_LATER', name='duplicatestatus'), nullable=False),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['contract_documents.id']),
        sa.ForeignKeyConstraint(['contract_id_a'], ['contracts.id']),
        sa.ForeignKeyConstraint(['contract_id_b'], ['contracts.id']),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contract_duplicates_id'), 'contract_duplicates', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('contract_duplicates')
    op.drop_table('contract_risk_flags')
    op.drop_table('contract_documents')
