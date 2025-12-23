"""Initial inventory schema

Revision ID: f22a6c12ff53
Revises: 
Create Date: 2025-12-08 03:25:15.286112

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f22a6c12ff53'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # --- Tabla Products ---
    op.create_table('products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('category', sa.String(), server_default="General", nullable=True),
        
        # NUEVO: Unidad de Medida
        sa.Column('measurement_unit', sa.String(), server_default="UNIT", nullable=False),
        
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        
        # CAMBIO: Numeric(12, 3) para soportar 1.500 Kg
        sa.Column('stock', sa.Numeric(precision=12, scale=3), server_default='0', nullable=True),
        
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=False) # SKU no único globalmente, sino por tenant (lógica app)
    op.create_index(op.f('ix_products_name'), 'products', ['name'], unique=False)
    op.create_index(op.f('ix_products_tenant_id'), 'products', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_products_category'), 'products', ['category'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_products_category'), table_name='products')
    op.drop_index(op.f('ix_products_tenant_id'), table_name='products')
    op.drop_index(op.f('ix_products_name'), table_name='products')
    op.drop_index(op.f('ix_products_sku'), table_name='products')
    op.drop_index(op.f('ix_products_id'), table_name='products')
    op.drop_table('products')