"""Initial hhrr schema

Revision ID: 6713d96a537a
Revises: 
Create Date: 2025-12-08 03:27:25.221700

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6713d96a537a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crear tabla de Horarios (Work Schedules)
    op.create_table('work_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('monday_start', sa.Time(), nullable=True),
        sa.Column('monday_end', sa.Time(), nullable=True),
        sa.Column('tuesday_start', sa.Time(), nullable=True),
        sa.Column('tuesday_end', sa.Time(), nullable=True),
        sa.Column('wednesday_start', sa.Time(), nullable=True),
        sa.Column('wednesday_end', sa.Time(), nullable=True),
        sa.Column('thursday_start', sa.Time(), nullable=True),
        sa.Column('thursday_end', sa.Time(), nullable=True),
        sa.Column('friday_start', sa.Time(), nullable=True),
        sa.Column('friday_end', sa.Time(), nullable=True),
        sa.Column('saturday_start', sa.Time(), nullable=True),
        sa.Column('saturday_end', sa.Time(), nullable=True),
        sa.Column('sunday_start', sa.Time(), nullable=True),
        sa.Column('sunday_end', sa.Time(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_work_schedules_id'), 'work_schedules', ['id'], unique=False)
    op.create_index(op.f('ix_work_schedules_tenant_id'), 'work_schedules', ['tenant_id'], unique=False)

    # 2. Crear tabla Empleados (Con la corrección y la relación ya listas)
    op.create_table('employees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=False),
        sa.Column('last_name', sa.String(), nullable=False),
        sa.Column('identification', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('position', sa.String(), nullable=True),
        sa.Column('department', sa.String(), nullable=True),
        sa.Column('manager_name', sa.String(), nullable=True),
        sa.Column('hired_at', sa.Date(), nullable=True),
        sa.Column('contract_type', sa.String(), nullable=True),
        sa.Column('schedule_id', sa.Integer(), nullable=True),
        sa.Column('salary', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('bonus_scheme', sa.String(), nullable=True),
        sa.Column('emergency_contact', sa.JSON(), nullable=True), # Ya corregido
        sa.Column('documents', sa.JSON(), nullable=True),
        sa.Column('performance_reviews', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['schedule_id'], ['work_schedules.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employees_email'), 'employees', ['email'], unique=False)
    op.create_index(op.f('ix_employees_id'), 'employees', ['id'], unique=False)
    op.create_index(op.f('ix_employees_identification'), 'employees', ['identification'], unique=False)
    op.create_index(op.f('ix_employees_tenant_id'), 'employees', ['tenant_id'], unique=False)

    # 3. Crear tabla Nómina
    op.create_table('payrolls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payrolls_id'), 'payrolls', ['id'], unique=False)
    op.create_index(op.f('ix_payrolls_tenant_id'), 'payrolls', ['tenant_id'], unique=False)

def downgrade() -> None:
    op.drop_table('payrolls')
    op.drop_table('employees')
    op.drop_table('work_schedules')
