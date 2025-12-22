"""Initial migration

Revision ID: 5c37e874e355
Revises: 
Create Date: 2025-12-08 03:15:09.013569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5c37e874e355'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crear Tabla Tenants (Con corrección is_active)
    op.create_table('tenants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('rif', sa.String(), nullable=False),
        sa.Column('business_name', sa.String(), nullable=False),
        sa.Column('address', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('invoice_format', sa.Enum('TICKET', 'FULL_PAGE', name='invoiceformat'), nullable=True),
        sa.Column('currency_display', sa.Enum('VES_ONLY', 'DUAL', 'MIXED_TOTAL', name='currencydisplay'), nullable=True),
        sa.Column('current_local_id', sa.String(), nullable=True),
        sa.Column('tax_active', sa.Boolean(), nullable=True),
        sa.Column('tax_type', sa.Enum('EXCLUSIVE', 'INCLUSIVE', name='taxtype'), nullable=True),
        sa.Column('tax_rate', sa.Integer(), nullable=True),
        sa.Column('plan', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True), # Corregido
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tenants_id'), 'tenants', ['id'], unique=False)
    op.create_index(op.f('ix_tenants_name'), 'tenants', ['name'], unique=False)

    # 2. Crear Tabla Users (Con campo full_name)
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True), # Agregado
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_tenants_name'), table_name='tenants')
    op.drop_index(op.f('ix_tenants_id'), table_name='tenants')
    op.drop_table('tenants')
    
    # Limpieza de Enums
    sa.Enum(name='invoiceformat').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='currencydisplay').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='taxtype').drop(op.get_bind(), checkfirst=True)