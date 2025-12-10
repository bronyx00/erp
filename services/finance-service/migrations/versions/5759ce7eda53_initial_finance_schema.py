"""Initial finance schema

Revision ID: 5759ce7eda53
Revises: 
Create Date: 2025-12-08 03:24:18.279097

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5759ce7eda53'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # --- 1. Tabla Facturas (Invoices) ---
    op.create_table('invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.Integer(), nullable=False),
        sa.Column('control_number', sa.String(), nullable=True),
        sa.Column('company_name_snapshot', sa.String(), nullable=True),
        sa.Column('company_rif_snapshot', sa.String(), nullable=True),
        sa.Column('company_address_snapshot', sa.String(), nullable=True),
        sa.Column('customer_name', sa.String(), nullable=True),
        sa.Column('customer_rif', sa.String(), nullable=True),
        sa.Column('customer_email', sa.String(), nullable=True),
        sa.Column('customer_address', sa.String(), nullable=True),
        sa.Column('customer_phone', sa.String(), nullable=True),
        sa.Column('subtotal_usd', sa.Numeric(precision=12, scale=2), server_default='0', nullable=True),
        sa.Column('tax_amount_usd', sa.Numeric(precision=12, scale=2), server_default='0', nullable=True),
        sa.Column('total_usd', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='USD', nullable=True),
        sa.Column('exchange_rate', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('amount_ves', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('status', sa.String(), server_default='ISSUED', nullable=True),
        sa.Column('is_synced_compliance', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by_email', sa.String(), nullable=True),
        sa.Column('created_by_role', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoices_id'), 'invoices', ['id'], unique=False)
    op.create_index(op.f('ix_invoices_tenant_id'), 'invoices', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_invoices_customer_email'), 'invoices', ['customer_email'], unique=False)

    # --- 2. Tabla Items de Factura ---
    op.create_table('invoice_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('product_name', sa.String(), nullable=True),
        sa.Column('quantity', sa.Integer(), server_default='1', nullable=True),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('total_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoice_items_id'), 'invoice_items', ['id'], unique=False)

    # --- 3. Tabla Pagos ---
    op.create_table('payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='USD', nullable=True),
        sa.Column('payment_method', sa.String(), nullable=True),
        sa.Column('reference', sa.String(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)

    # --- 4. Tabla Tasas de Cambio ---
    op.create_table('exchange_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('currency_from', sa.String(length=3), server_default='USD', nullable=True),
        sa.Column('currency_to', sa.String(length=3), server_default='VES', nullable=True),
        sa.Column('rate', sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column('source', sa.String(), server_default='BCV', nullable=True),
        sa.Column('acquired_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exchange_rates_id'), 'exchange_rates', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_exchange_rates_id'), table_name='exchange_rates')
    op.drop_table('exchange_rates')
    
    op.drop_index(op.f('ix_payments_id'), table_name='payments')
    op.drop_table('payments')
    
    op.drop_index(op.f('ix_invoice_items_id'), table_name='invoice_items')
    op.drop_table('invoice_items')
    
    op.drop_index(op.f('ix_invoices_customer_email'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_tenant_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_id'), table_name='invoices')
    op.drop_table('invoices')