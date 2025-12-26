from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, Date, Text, JSON, ForeignKey, Time
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import enum

class Employee(Base):
    """
    Ficha principal del empleado.
    Incluye datos personales, laborales y configuración de compensación.
    """
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    
    # --- DATOS PERSONALES ---
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    identification = Column(String, nullable=False, index=True) 
    email = Column(String, index=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    birth_date = Column(Date, nullable=True)
    
    # --- DATOS LABORALES ---
    position = Column(String) 
    department = Column(String, nullable=True)     # Ej: Ventas, Almacén
    
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)     # ID de otro empleado (Supervisor)
    manager = relationship("Employee", remote_side=[id], backref="subordinates")
    
    hired_at = Column(Date, nullable=True)
    contract_type = Column(String, default="UNDEFINED") # Indefinido, Determinado
    
    # --- RELACION CON HORARIO ---
    schedule_id = Column(Integer, ForeignKey("work_schedules.id"), nullable=True)
    schedule = relationship("WorkSchedule")
    
    # --- COMPENSACIÓN ---
    salary = Column(Numeric(10, 2), default=0)
    bonus_scheme = Column(String, nullable=True)    # Ej: "3% Comisión"
    
    # --- DATOS COMPLEJOS ---
    emergency_contact = Column(JSON, nullable=True)
    documents = Column(JSON, default=list)
    performance_reviews = Column(JSON, default=list)
    
    # --- ESTADO ---
    status = Column(String, default="Active")       # ACTIVE, ON LEAVE, TERMINATED
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Payroll(Base):
    """
    Recibo de Nómina generado.
    Guarda el histórico de pagos, deducciones y aportes.
    """
    __tablename__ = "payrolls"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    
    # Relación con el Empleado
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    employee = relationship("Employee")
    
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    # --- INGRESOS ---
    base_salary = Column(Numeric(10, 2), default=0)         # Sueldo Base
    
    # Total de bonos que SÍ pagan impuestos (salariales)
    taxable_bonuses = Column(Numeric(10, 2), default=0)
    # Total de bonos que NO pagan impuestos (No salariales)
    non_taxable_bonuses = Column(Numeric(10, 2), default=0)
    
    total_earnings = Column(Numeric(10, 2), nullable=False) # Total Ingresos (Bruto)
    
    # --- RETENCIONES AL TRABAJADOR ---
    ivss_base = Column(Numeric(10, 2), default=0)           # Base sobre la que se calculó el IVSS
    
    # (IVSS - 4%)
    ivss_employee = Column(Numeric(10, 2), default=0) 
    # (FAOV - 1%)
    faov_employee = Column(Numeric(10, 2), default=0)
    # (ISLR - Variable)
    islr_retention = Column(Numeric(10, 2), default=0)
    
    total_deductions = Column(Numeric(10, 2), default=0)    # Total Deducciones
    
    # --- APORTES PATRONALES ---
    # Estos son costos para la empresa, no se deducen del salario del empleado.
    # Seguridad Social (IVSS - 9%, 10% o 11%)
    ivss_employer = Column(Numeric(10, 2), default=0)
    # Fondo de Vivienda (FAOV - 2%)
    faov_employer = Column(Numeric(10, 2), default=0)
    
    # --- PAGO NETO ---
    net_pay = Column(Numeric(10, 2), nullable=False)
    
    # Detalle en JSON para saber qué bonos se pagaron exactamente
    details = Column(JSON, default=dict) # Ej: {"Bono Prod": 50, "Sueldo": 40}
    
    status = Column(String, default="DRAFT")                # DRAFT, CALCULATED, PAID
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WorkSchedule(Base):
    """Definición de turnos laborales."""
    __tablename__ = "work_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=True)
    name = Column(String, nullable=False) # Ej: "Diurno Lunes-Viernes"
    
    # Horas (Formato 24h)
    monday_start = Column(Time, nullable=True)
    monday_end = Column(Time, nullable=True)
    tuesday_start = Column(Time, nullable=True)
    tuesday_end = Column(Time, nullable=True)
    wednesday_start = Column(Time, nullable=True)
    wednesday_end = Column(Time, nullable=True)
    thursday_start = Column(Time, nullable=True)
    thursday_end = Column(Time, nullable=True)
    friday_start = Column(Time, nullable=True)
    friday_end = Column(Time, nullable=True)
    saturday_start = Column(Time, nullable=True)
    saturday_end = Column(Time, nullable=True)
    sunday_start = Column(Time, nullable=True)
    sunday_end = Column(Time, nullable=True)
    
    is_active = Column(Boolean, default=True)

class IncomeCalculationType(str, enum.Enum):
    FIXED = "FIXED"                     # Monto fijo (Ej: Bono Transporte $20)
    PERCENTAGE_OF_SALARY = "SALARY_PCT" # % del Sueldo Base (Ej: Antiguedad)
    PERCENTAGE_OF_SALES = "SALES_PCT"   # % de Ventas del Periodo (Comisiones)
    
class IncomeConcept(Base):
    """
    Catálogo de Conceptos de Ingreso (Ej: Bono Producción, Comisión Ventas).
    Define si el concepto es 'Salarial' (afecta IVSS/Prestaciones) o no.
    """
    __tablename__ = "income_concepts"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    
    name = Column(String, nullable=False)   # Ej: "Bono de Productividad"
    is_active = Column(Boolean, default=True)
    
    # Define si este ingreso paga impuestos o no
    # True = Se suma al salario base para IVSS/FAOV
    # False = No paga impuestos
    is_salary = Column(Boolean, default=False)
    
    # Tipo de cálculo: FIXED (Monto fijo) o PERCENTAGE (% del sueldo base)
    calculation_type = Column(String, default="FIXED")
    
class EmployeeRecurringIncome(Base):
    """
    Asigna un concepto a un empleado específico.
    Ej: Juan tiene un 'Bono de Producción' de $50.
    """
    __tablename__ = "employee_recurring_incomes"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    concept_id = Column(Integer, ForeignKey("income_concepts.id"), nullable=False)
    
    amount = Column(Numeric(10, 2), default=0) # Valor (Dinero o porcentaje)
    
    employee = relationship("Employee", backref="recurring_incomes")
    concept = relationship("IncomeConcept")
    
class PayrollGlobalSettings(Base):
    """
    Configuración Global de Nómina (Tasas, Topes, Unidad Tributaria, etc).
    Permite cambiar los valores sin tocar código.
    """
    __tablename__ = "payroll_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    
    # Valores Monetarios Globales
    official_minumin_wage = Column(Numeric(10, 2), default=1.00)    # Salario Mínimo Oficial
    food_bonus_value = Column(Numeric(10, 2), default=40.00)        # Cestaticket
    
    # Porcentajes de Ley
    ivss_employee_rate = Column(Numeric(5, 4), default=0.04)
    ivss_employer_rate = Column(Numeric(5, 4), default=0.09)
    ivss_cap_min_wages = Column(Integer, default=5)
    
    faov_employee_rate = Column(Numeric(5, 4), default=0.01)
    faov_employer_rate = Column(Numeric(5, 4), default=0.02)
    
    # Flags de Comportamiento
    calculate_taxes_on_bonuses = Column(Boolean, default=False)
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
class SupervisorNote(Base):
    """Bitácora de anotaciones de supervisores."""
    __tablename__ = "supervisor_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    supervisor_email = Column(String, nullable=False)
    
    category = Column(String, default="GENERAL")
    content = Column(Text, nullable=False)
    is_private = Column(Boolean, default=False) # Si es True, el empleado no la ve
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación
    employee = relationship("Employee", backref="notes")