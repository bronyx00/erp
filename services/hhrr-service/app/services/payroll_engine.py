import json
import os
import aio_pika
import httpx
from decimal import Decimal
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Employee, Payroll, PayrollGlobalSettings, EmployeeRecurringIncome

# RabbitMQ Connection URL
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

# URL interna del servicio de facturacion
FINANCE_SERVICE_URL = os.getenv("FINANCE_SERVICE", "http://finance-service:8000")

class PayrollCalculator:
    
    @staticmethod
    async def get_employee_sales_total(tenant_id: int, employee_id: int, start_date, end_date):
        """
        Consulta al servicio de Finanzas cuánto vendió este empleado en el periodo
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{FINANCE_SERVICE_URL}/api/reports/sales-total",
                    params={
                        "tenant_id": tenant_id,
                        "employee_id": employee_id,
                        "start_date": str(start_date),
                        "end_date": str(end_date)
                    },
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return Decimal(str(data.get("total_sales", 0)))
                else:
                    print(f" [!] Error obteniendo las ventas: {response.status_code}")
                    return Decimal(0)
        except Exception as e:
            print(f" [!] Error conectando con Finance Service: {e}")
            return Decimal(0)
                
    
    @staticmethod
    async def get_settings(db: AsyncSession, tenant_id: int):
        """Obtiene la configuración activa o crea una por defecto"""
        result = await db.execute(select(PayrollGlobalSettings).where(PayrollGlobalSettings.tenant_id == tenant_id))
        settings = result.scalars().first()
        if not settings:
            # Crear defaults si no existe
            settings = PayrollGlobalSettings(tenant_id=tenant_id)
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
        return settings
    
    @staticmethod
    async def calculate_concepts(salary_base, recurring_incomes, sales_total_period=Decimal(0)):
        """
        Calcula cada concepto según su tipo (Fijo, % Salario, % Ventas)
        """
        taxable_total = Decimal(0)
        non_taxable_total = Decimal(0)
        details = {}
        
        for item in recurring_incomes:
            amount = Decimal(0)
            calc_type = item.concept.calculation_type
            item_value = item.value
            
            if calc_type == "FIXED":
                amount = item_value
                
            elif calc_type == "SALARY_PCT":
                # item_value es porcentaje (Ej. 10 para 10%)}
                amount = salary_base * (item_value / Decimal(100))
                
            elif calc_type == "SALES_PCT":
                # item_value es % de comisión (Ej. 3 para 3%)
                # Usa el total de ventas traído del Finance-Service
                amount = sales_total_period * (item_value / Decimal(100))
            
            # Redondear
            amount = round(amount, 2)
                
            # Guardar detalle
            details[item.concept.name] = float(amount)
            
            if item.concept.is_salary:
                taxable_total += amount
            else:
                non_taxable_total += amount
        
        return taxable_total, non_taxable_total, details

async def generate_payroll_event(payroll: Payroll, db: AsyncSession):
    """
    Calcula la nómina completa usando configuraciones dinámicas de BD.
    Configuración -> Ventas -> Conceptos -> Impuestos -> Contabilidad.
    """
    # Obtener Configuración Global
    settings = await PayrollCalculator.get_settings(db, payroll.tenant_id)
    
    # Cargar Empleado con sus Ingresos Recurrentes
    result = await db.execute(
        select(Employee)
        .options(selectinload(Employee.recurring_incomes).selectinload(EmployeeRecurringIncome.concept))
        .where(Employee.id == payroll.employee_id)
    )
    employee = result.scalars().first()
    if not employee:
        raise ValueError("Empleado no encontrado")
    
    base_salary = Decimal(str(employee.salary or 0))
    
    # Obtiene ventas del periodo
    has_sales_concept = any(ri.concept.calculation_type == "SALES_PCT" for ri in employee.recurring_incomes)
    sales_total = Decimal(0)
    
    if has_sales_concept: 
        print(f" [i] Obteniendo ventas del empleado {employee.id}...", flush=True)
        sales_total = await PayrollCalculator.get_employee_sales_total(
            payroll.tenant_id,
            employee.id,
            payroll.period_start,
            payroll.period_end
        )
        print(f" [v] Ventas encontradas: {sales_total}", flush=True)
    
    # Calcular Bonos y Comisiones
    taxable_bonuses, non_taxable_bonuses, income_details = await PayrollCalculator.calculate_concepts(
        base_salary, employee.recurring_incomes, sales_total_period=sales_total
    )
    
    # Definir la Base Imponible (Sueldo integral para tributos)
    comprehensive_salary = base_salary + taxable_bonuses

    # Calcular Topes de Ley
    ivss_cap = settings.official_minumin_wage * settings.ivss_cap_min_wages
    
    # La base del IVSS es el menor entre el suelto integral y el tope
    ivss_base = min(comprehensive_salary, ivss_cap)
    
    # La base de FAOV no suele tener tope
    faov_base = comprehensive_salary
    
    # Calcular Retenciones
    ivss_emp = ivss_base * settings.ivss_employer_rate
    faov_emp = faov_base * settings.faov_employer_rate
    
    # Calcular Aportes Patronales
    ivss_comp = ivss_base * settings.ivss_employer_rate
    faov_comp = faov_base * settings.faov_employer_rate
    
    # Actualizar Objeto Payroll
    payroll.base_salary = base_salary
    payroll.taxable_bonuses = taxable_bonuses
    payroll.non_taxable_bonuses = non_taxable_bonuses
    payroll.total_earnings = comprehensive_salary + non_taxable_bonuses
    
    payroll.ivss_base = ivss_base # Guarda la base usada para auditoria
    payroll.ivss_employee = round(ivss_emp, 2)
    payroll.faov_employee = round(faov_emp, 2)
    payroll.islr_retention = Decimal(0)
    
    payroll.total_deductions = payroll.ivss_employee + payroll.faov_employee
    
    payroll.ivss_employer = round(ivss_comp, 2)
    payroll.faov_employer = round(faov_comp, 2)
    
    payroll.net_pay = payroll.total_earnings - payroll.total_deductions
    
    # Info de ventas al detalle para transparencia
    if has_sales_concept:
        income_details["_meta_sales_base"] = float(sales_total)
    
    payroll.details = income_details
    payroll.status = "CALCULATED"
    
    db.add(payroll)
    await db.commit()
    await db.refresh(payroll)
    
    # Enviar a Contabilidad
    await publish_payroll_event(payroll)
    
    return payroll

async def publish_payroll_event(payroll: Payroll):
    """
    Publica el mensaje que el trabajador de contabilidad está escuchando.
    """
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        
        # Declarar el mismo cambio utilizado en Contabilidad
        exchange = await channel.declare_exchange("erp_events", aio_pika.ExchangeType.TOPIC, durable=True)
        
        # Carga útil que coincide con las expectativas contables
        message_body = {
            "event": "payroll.calculated",
            "id": payroll.id,
            "tenant_id": payroll.tenant_id,
            "period_start": str(payroll.period_start),
            "period_end": str(payroll.period_end),
            "employee_id": payroll.employee_id,
            
            # Datos Financieros
            "total_earnings": float(payroll.total_earnings),
            "base_salary": float(payroll.base_salary),
            
            # Desglose para Contabilidad (Salarial va a Gastos Sueldos, Bonos a Gastos Bonos)
            "taxable_earnings": float(payroll.base_salary + payroll.taxable_bonuses),
            "non_taxable_earnings": float(payroll.non_taxable_bonuses),
            
            "ivss_employee": float(payroll.ivss_employee),
            "faov_employee": float(payroll.faov_employee),
            "ivss_employer": float(payroll.ivss_employer),
            "faov_employer": float(payroll.faov_employer),
            "net_pay": float(payroll.net_pay)
        }
        
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(message_body).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key="payroll.calculated" # ¡Importante! Debe coincidir con el worker
        )
        print(f" [x] Enviando Evento de Pago #{payroll.id} a Contabilidad", flush=True)