"""Initial Finance Schema with Cash Close

Revision ID: aa0777c65c62
Revises: 
Create Date: 2024-10-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa0777c65c62'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # --- 1. Finance Settings ---
    op.create_table('finance_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('enable_salesperson_selection', sa.Boolean(), nullable=True),
        sa.Column('default_currency', sa.String(), nullable=True),
        sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_finance_settings_id'), 'finance_settings', ['id'], unique=False)
    op.create_index(op.f('ix_finance_settings_tenant_id'), 'finance_settings', ['tenant_id'], unique=False)

    # --- 2. Cash Closes (Cierre de Caja) ---
    op.create_table('cash_closes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        
        # Totales USD
        sa.Column('total_sales_usd', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('total_tax_usd', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('total_discount_usd', sa.Numeric(precision=12, scale=2), nullable=True),
        
        # Totales VES
        sa.Column('total_sales_ves', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('total_tax_ves', sa.Numeric(precision=20, scale=2), nullable=True),
        
        # Desglose USD
        sa.Column('total_cash_usd', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('total_debit_card_usd', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('total_transfer_usd', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('total_credit_sales_usd', sa.Numeric(precision=12, scale=2), nullable=True),
        
        # Desglose VES
        sa.Column('total_cash_ves', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('total_debit_card_ves', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('total_transfer_ves', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('total_credit_sales_ves', sa.Numeric(precision=20, scale=2), nullable=True),
        
        # Arqueo y Diferencia
        sa.Column('declared_cash_usd', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('declared_cash_ves', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('difference_usd', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('difference_ves', sa.Numeric(precision=12, scale=2), nullable=True),
        
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cash_closes_id'), 'cash_closes', ['id'], unique=False)
    op.create_index(op.f('ix_cash_closes_tenant_id'), 'cash_closes', ['tenant_id'], unique=False)

    # --- 3. Exchange Rates ---
    op.create_table('exchange_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('currency_from', sa.String(length=3), nullable=True),
        sa.Column('currency_to', sa.String(length=3), nullable=True),
        sa.Column('rate', sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('acquired_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exchange_rates_id'), 'exchange_rates', ['id'], unique=False)

    # --- 4. Quotes (Cotizaciones) ---
    op.create_table('quotes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('quote_number', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('customer_name', sa.String(), nullable=True),
        sa.Column('customer_rif', sa.String(), nullable=True),
        sa.Column('customer_email', sa.String(), nullable=True),
        sa.Column('customer_address', sa.Text(), nullable=True),
        sa.Column('customer_phone', sa.String(), nullable=True),
        
        sa.Column('company_name', sa.String(), nullable=True),
        sa.Column('company_rif', sa.String(), nullable=True),
        sa.Column('company_address', sa.String(), nullable=True),
        
        sa.Column('date_issued', sa.Date(), nullable=False),
        sa.Column('date_expires', sa.Date(), nullable=False),
        
        sa.Column('currency', sa.String(), nullable=True),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('total', sa.Numeric(precision=12, scale=2), nullable=True),
        
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('terms', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by_email', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quotes_id'), 'quotes', ['id'], unique=False)
    op.create_index(op.f('ix_quotes_quote_number'), 'quotes', ['quote_number'], unique=False)
    op.create_index(op.f('ix_quotes_tenant_id'), 'quotes', ['tenant_id'], unique=False)

    # --- 5. Invoices (Facturas) ---
    op.create_table('invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('salesperson_id', sa.Integer(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.Integer(), nullable=False),
        sa.Column('control_number', sa.String(), nullable=True),
        
        # Datos Empresa Snapshot
        sa.Column('company_name', sa.String(), nullable=True),
        sa.Column('company_rif', sa.String(), nullable=True),
        sa.Column('company_address', sa.String(), nullable=True),
        
        # Datos Cliente Snapshot
        sa.Column('customer_name', sa.String(), nullable=True),
        sa.Column('customer_rif', sa.String(), nullable=True),
        sa.Column('customer_email', sa.String(), nullable=True),
        sa.Column('customer_address', sa.String(), nullable=True),
        sa.Column('customer_phone', sa.String(), nullable=True),
        
        # Montos
        sa.Column('subtotal_usd', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('tax_amount_usd', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('total_usd', sa.Numeric(precision=12, scale=2), nullable=False),
        
        # Moneda
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('exchange_rate', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('amount_ves', sa.Numeric(precision=20, scale=2), nullable=True),
        
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('is_synced_compliance', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by_role', sa.String(), nullable=True),
        
        # Relación con Cash Close
        sa.Column('cash_close_id', sa.Integer(), nullable=True),
        
        sa.ForeignKeyConstraint(['cash_close_id'], ['cash_closes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoices_cash_close_id'), 'invoices', ['cash_close_id'], unique=False)
    op.create_index(op.f('ix_invoices_customer_email'), 'invoices', ['customer_email'], unique=False)
    op.create_index(op.f('ix_invoices_id'), 'invoices', ['id'], unique=False)
    op.create_index(op.f('ix_invoices_salesperson_id'), 'invoices', ['salesperson_id'], unique=False)
    op.create_index(op.f('ix_invoices_tenant_id'), 'invoices', ['tenant_id'], unique=False)

    # --- 6. Invoice Items ---
    op.create_table('invoice_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('product_name', sa.String(), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('total_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoice_items_id'), 'invoice_items', ['id'], unique=False)

    # --- 7. Payments ---
    op.create_table('payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('payment_method', sa.String(), nullable=True),
        sa.Column('reference', sa.String(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)

    # --- 8. Quote Items ---
    op.create_table('quote_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quote_id', sa.Integer(), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('product_name', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('total_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quote_items_id'), 'quote_items', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_quote_items_id'), table_name='quote_items')
    op.drop_table('quote_items')
    
    op.drop_index(op.f('ix_payments_id'), table_name='payments')
    op.drop_table('payments')
    
    op.drop_index(op.f('ix_invoice_items_id'), table_name='invoice_items')
    op.drop_table('invoice_items')
    
    op.drop_index(op.f('ix_invoices_tenant_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_salesperson_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_customer_email'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_cash_close_id'), table_name='invoices')
    op.drop_table('invoices')
    
    op.drop_index(op.f('ix_quotes_tenant_id'), table_name='quotes')
    op.drop_index(op.f('ix_quotes_quote_number'), table_name='quotes')
    op.drop_index(op.f('ix_quotes_id'), table_name='quotes')
    op.drop_table('quotes')
    
    op.drop_index(op.f('ix_exchange_rates_id'), table_name='exchange_rates')
    op.drop_table('exchange_rates')
    
    op.drop_index(op.f('ix_cash_closes_tenant_id'), table_name='cash_closes')
    op.drop_index(op.f('ix_cash_closes_id'), table_name='cash_closes')
    op.drop_table('cash_closes')
    
    op.drop_index(op.f('ix_finance_settings_tenant_id'), table_name='finance_settings')
    op.drop_index(op.f('ix_finance_settings_id'), table_name='finance_settings')
    op.drop_table('finance_settings')