"""Add quotes table

Revision ID: add_quotes_table
Revises: 5759ce7eda53
Create Date: 2025-12-10 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_quotes_table'
down_revision: Union[str, Sequence[str], None] = '5759ce7eda53' # Tu migración anterior
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Quotes
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
        sa.Column('date_issued', sa.Date(), nullable=False),
        sa.Column('date_expires', sa.Date(), nullable=False),
        sa.Column('currency', sa.String(), nullable=True),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=True),
        sa.Column('tax_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('total', sa.Numeric(12, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('terms', sa.Text(), nullable=True),
        sa.Column('created_by_email', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quotes_id'), 'quotes', ['id'], unique=False)
    op.create_index(op.f('ix_quotes_quote_number'), 'quotes', ['quote_number'], unique=False)
    op.create_index(op.f('ix_quotes_tenant_id'), 'quotes', ['tenant_id'], unique=False)

    # Quote Items
    op.create_table('quote_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quote_id', sa.Integer(), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('product_name', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('unit_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('total_price', sa.Numeric(12, 2), nullable=True),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quote_items_id'), 'quote_items', ['id'], unique=False)

def downgrade() -> None:
    op.drop_table('quote_items')
    op.drop_table('quotes')