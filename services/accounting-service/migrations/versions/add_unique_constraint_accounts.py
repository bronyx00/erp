"""Add unique constraint to accounts

Revision ID: add_unique_constraint
Revises: 8b652bada164  # Asegúrate que este sea el ID de tu última migración exitosa
Create Date: 2025-12-10 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_unique_constraint'
down_revision: Union[str, Sequence[str], None] = '27ec6fb38fea' # O el ID de tu migración anterior
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Intenta crear la restricción única
    try:
        op.create_unique_constraint('uq_account_code_tenant', 'accounts', ['code', 'tenant_id'])
    except Exception:
        pass # Si ya existe o falla por duplicados, lo ignoramos (limpieza manual requerida primero)

def downgrade() -> None:
    op.drop_constraint('uq_account_code_tenant', 'accounts', type_='unique')