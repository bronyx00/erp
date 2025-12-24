"""initial_hhrr_schema_v4

Revision ID: 1a2b3c4d5e6f
Revises: 
Create Date: 2025-12-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # --- 1. Income Concepts ---
    op.create_table('income_concepts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_salary', sa.Boolean(), nullable=True),
        sa.Column('calculation_type', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_income_concepts_id'), 'income_concepts', ['id'], unique=False)
    op.create_index(op.f('ix_income_concepts_tenant_id'), 'income_concepts', ['tenant_id'], unique=False)

    # --- 2. Payroll Settings ---
    op.create_table('payroll_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('official_minumin_wage', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('food_bonus_value', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ivss_employee_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('ivss_employer_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('ivss_cap_min_wages', sa.Integer(), nullable=True),
        sa.Column('faov_employee_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('faov_employer_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('calculate_taxes_on_bonuses', sa.Boolean(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payroll_settings_id'), 'payroll_settings', ['id'], unique=False)
    op.create_index(op.f('ix_payroll_settings_tenant_id'), 'payroll_settings', ['tenant_id'], unique=False)

    # --- 3. Work Schedules ---
    op.create_table('work_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
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

    # --- 4. Employees (Depende de Work Schedules) ---
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
        sa.Column('manager_id', sa.Integer(), nullable=True),
        sa.Column('hired_at', sa.Date(), nullable=True),
        sa.Column('contract_type', sa.String(), nullable=True),
        sa.Column('schedule_id', sa.Integer(), nullable=True),
        sa.Column('salary', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('bonus_scheme', sa.String(), nullable=True),
        sa.Column('emergency_contact', sa.JSON(), nullable=True),
        sa.Column('documents', sa.JSON(), nullable=True),
        sa.Column('performance_reviews', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['manager_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['schedule_id'], ['work_schedules.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employees_email'), 'employees', ['email'], unique=False)
    op.create_index(op.f('ix_employees_id'), 'employees', ['id'], unique=False)
    op.create_index(op.f('ix_employees_identification'), 'employees', ['identification'], unique=False)
    op.create_index(op.f('ix_employees_tenant_id'), 'employees', ['tenant_id'], unique=False)

    # --- 5. Tablas dependientes de Employee ---
    op.create_table('employee_recurring_incomes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('concept_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['concept_id'], ['income_concepts.id'], ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_recurring_incomes_id'), 'employee_recurring_incomes', ['id'], unique=False)

    op.create_table('payrolls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('base_salary', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('taxable_bonuses', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('non_taxable_bonuses', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('total_earnings', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('ivss_base', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ivss_employee', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('faov_employee', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('islr_retention', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('total_deductions', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ivss_employer', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('faov_employer', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('net_pay', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payrolls_id'), 'payrolls', ['id'], unique=False)
    op.create_index(op.f('ix_payrolls_tenant_id'), 'payrolls', ['tenant_id'], unique=False)

    op.create_table('supervisor_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('supervisor_email', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_private', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_supervisor_notes_id'), 'supervisor_notes', ['id'], unique=False)
    op.create_index(op.f('ix_supervisor_notes_tenant_id'), 'supervisor_notes', ['tenant_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_supervisor_notes_tenant_id'), table_name='supervisor_notes')
    op.drop_index(op.f('ix_supervisor_notes_id'), table_name='supervisor_notes')
    op.drop_table('supervisor_notes')
    op.drop_index(op.f('ix_payrolls_tenant_id'), table_name='payrolls')
    op.drop_index(op.f('ix_payrolls_id'), table_name='payrolls')
    op.drop_table('payrolls')
    op.drop_index(op.f('ix_employee_recurring_incomes_id'), table_name='employee_recurring_incomes')
    op.drop_table('employee_recurring_incomes')
    op.drop_index(op.f('ix_employees_tenant_id'), table_name='employees')
    op.drop_index(op.f('ix_employees_identification'), table_name='employees')
    op.drop_index(op.f('ix_employees_id'), table_name='employees')
    op.drop_index(op.f('ix_employees_email'), table_name='employees')
    op.drop_table('employees')
    op.drop_index(op.f('ix_work_schedules_tenant_id'), table_name='work_schedules')
    op.drop_index(op.f('ix_work_schedules_id'), table_name='work_schedules')
    op.drop_table('work_schedules')
    op.drop_index(op.f('ix_payroll_settings_tenant_id'), table_name='payroll_settings')
    op.drop_index(op.f('ix_payroll_settings_id'), table_name='payroll_settings')
    op.drop_table('payroll_settings')
    op.drop_index(op.f('ix_income_concepts_tenant_id'), table_name='income_concepts')
    op.drop_index(op.f('ix_income_concepts_id'), table_name='income_concepts')
    op.drop_table('income_concepts')