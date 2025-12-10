"""Initial accounting schema

Revision ID: 27ec6fb38fea
Revises: 
Create Date: 2025-12-08 03:28:08.747565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27ec6fb38fea'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. Tabla Accounts ---
    op.create_table('accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('account_type', sa.String(), nullable=False),
        sa.Column('level', sa.Integer(), server_default='1', nullable=True),
        sa.Column('is_transactional', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('balance', sa.Numeric(precision=12, scale=2), server_default='0', nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_accounts_code'), 'accounts', ['code'], unique=False)
    op.create_index(op.f('ix_accounts_id'), 'accounts', ['id'], unique=False)
    op.create_index(op.f('ix_accounts_tenant_id'), 'accounts', ['tenant_id'], unique=False)

    # --- 2. Tabla Ledger Entries (Asientos) ---
    op.create_table('ledger_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('reference', sa.String(), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ledger_entries_id'), 'ledger_entries', ['id'], unique=False)
    op.create_index(op.f('ix_ledger_entries_tenant_id'), 'ledger_entries', ['tenant_id'], unique=False)

    # --- 3. Tabla Ledger Lines (Detalle Asiento) ---
    op.create_table('ledger_lines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entry_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('debit', sa.Numeric(precision=12, scale=2), server_default='0', nullable=True),
        sa.Column('credit', sa.Numeric(precision=12, scale=2), server_default='0', nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['entry_id'], ['ledger_entries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ledger_lines_id'), 'ledger_lines', ['id'], unique=False)

    # --- 4. Tabla Transactions (Historial simple) ---
    op.create_table('transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('transaction_type', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('reference_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_id'), 'transactions', ['id'], unique=False)
    op.create_index(op.f('ix_transactions_tenant_id'), 'transactions', ['tenant_id'], unique=False)

def downgrade() -> None:
    # Orden inverso para borrar
    op.drop_index(op.f('ix_transactions_tenant_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_id'), table_name='transactions')
    op.drop_table('transactions')
    
    op.drop_index(op.f('ix_ledger_lines_id'), table_name='ledger_lines')
    op.drop_table('ledger_lines')
    
    op.drop_index(op.f('ix_ledger_entries_tenant_id'), table_name='ledger_entries')
    op.drop_index(op.f('ix_ledger_entries_id'), table_name='ledger_entries')
    op.drop_table('ledger_entries')
    
    op.drop_index(op.f('ix_accounts_tenant_id'), table_name='accounts')
    op.drop_index(op.f('ix_accounts_id'), table_name='accounts')
    op.drop_index(op.f('ix_accounts_code'), table_name='accounts')
    op.drop_table('accounts')
