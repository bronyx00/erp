import json
import os
import aio_pika
import httpx
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Employee, Payroll, PayrollGlobalSettings, EmployeeRecurringIncome
from app.schemas import PayrollBulkCreateRequest, PayrollBulkPayRequest

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
    async def calculate_concepts(salary_base, recurring_incomes, sales_total_period=Decimal(0), days_in_period=30):
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
                # Ejemplo: Bono mensual 100$. Si trabajo 15 días -> (100/30)*15 = 50$
                daily_val = item_value / Decimal(30)
                amount = daily_val * Decimal(days_in_period)
                
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

async def generate_payroll_event(payroll: Payroll, db: AsyncSession, publish: bool = True):
    """
    Calcula la nómina completa usando configuraciones dinámicas de BD.
    Configuración -> Ventas -> Conceptos -> Impuestos -> Contabilidad.
    
    param: publish: Si es False, NO envía el evento a RabbitMQ (útil para pagos masivos).
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
    
    # --- LÓGICA DE DÍAS ---
    days_in_period = (payroll.period_end - payroll.period_start).days + 1
    
    if days_in_period <= 0: days_in_period = 1
    if days_in_period > 30: days_in_period = 30
    
    monthly_salary = Decimal(str(employee.salary or 0))
    daily_salary = monthly_salary / Decimal(30)
    
    # Sueldo Base del Periodo
    base_salary_period = round(daily_salary * Decimal(days_in_period), 2)
    
    # Ventas del Periodo
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

    # Calcular Bonos (Pasamos días para prorratear fijos) 
    taxable_bonuses, non_taxable_bonuses, income_details = await PayrollCalculator.calculate_concepts(
        base_salary_period, 
        employee.recurring_incomes, 
        sales_total_period=sales_total,
        days_in_period=days_in_period 
    )
    
    # Base Imponible del Periodo
    comprehensive_salary_period = base_salary_period + taxable_bonuses
    
    # El tope es mensual (5 salarios mínimos), debemos ajustarlo a los días de pago
    monthly_ivss_cap = settings.official_minumin_wage * settings.ivss_cap_min_wages
    daily_ivss_cap = monthly_ivss_cap / Decimal(30)
    period_ivss_cap = daily_ivss_cap * Decimal(days_in_period)
    
    # La base del IVSS es el menor entre el suelto integral y el tope
    ivss_base = min(comprehensive_salary_period, period_ivss_cap)
    
    # La base de FAOV no suele tener tope
    faov_base = comprehensive_salary_period
    
    # Calcular Retenciones
    ivss_emp = ivss_base * settings.ivss_employee_rate
    faov_emp = faov_base * settings.faov_employee_rate
    
    # Calcular Aportes Patronales
    ivss_comp = ivss_base * settings.ivss_employer_rate
    faov_comp = faov_base * settings.faov_employer_rate
    
    # Actualizar Objeto Payroll
    payroll.base_salary = base_salary_period
    payroll.taxable_bonuses = taxable_bonuses
    payroll.non_taxable_bonuses = non_taxable_bonuses
    payroll.total_earnings = comprehensive_salary_period + non_taxable_bonuses
    
    payroll.ivss_base = ivss_base # Guarda la base usada para auditoria
    payroll.ivss_employee = round(ivss_emp, 2)
    payroll.faov_employee = round(faov_emp, 2)
    payroll.islr_retention = Decimal(0)
    
    payroll.total_deductions = payroll.ivss_employee + payroll.faov_employee
    
    payroll.ivss_employer = round(ivss_comp, 2)
    payroll.faov_employer = round(faov_comp, 2)
    
    payroll.net_pay = payroll.total_earnings - payroll.total_deductions
    
    # Metadata útil para el recibo
    income_details["_meta_days_worked"] = days_in_period
    if has_sales_concept:
        income_details["_meta_sales_base"] = float(sales_total)
        
    payroll.details = income_details
    payroll.status = "CALCULATED"
    
    db.add(payroll)
    await db.commit()
    await db.refresh(payroll)
    
    # Enviar a Contabilidad. Solo si es explicita
    if publish:
        await publish_payroll_event(payroll)
    
    return payroll

async def process_bulk_payment(
    db: AsyncSession,
    request: PayrollBulkPayRequest,
    tenant_id: int
):
    """
    Procesa el pago de múltiples nóminas y genera un solo evento contable.
    """
    # 1. Buscar las nóminas
    query = select(Payroll).filter(
        Payroll.id.in_(request.payroll_ids),
        Payroll.tenant_id == tenant_id,
        Payroll.status != "PAID" # Solo procesar las que no estén pagadas
    )
    result = await db.execute(query)
    payrolls = result.scalars().all()
    
    if not payrolls:
        raise ValueError("No se encontraron nóminas pendientes.")
    
    agg_stats = {
        "total_net_pay": Decimal(0),      # Lo que sale del Banco
        "total_earnings": Decimal(0),     # Gasto total (Sueldos + Bonos)
        "total_employer_cost": Decimal(0), # Aportes Patronales (Gasto extra)
        
        # Desglose de pasivos
        "liability_ivss_total": Decimal(0), # IVSS Empleado + IVSS Empresa
        "liability_faov_total": Decimal(0), # FAOV Empleado + FAOV Empresa
        "liability_other_total": Decimal(0) # Otras retenciones (ISLR, etc)
    }
    
    processed_ids = []
    
    # 2. Actualizar estados y sumar
    for payroll in payrolls:
        # 1. Calcula sueldo sin emitir evento
        updated_payroll = await generate_payroll_event(payroll, db, publish=False)
        
        # 2. Actualiza a PAGADO
        updated_payroll.status = "PAID"
        db.add(updated_payroll)
        
        # 3. Sumar a los acumuladores globales
        agg_stats["total_net_pay"] += updated_payroll.net_pay
        agg_stats["total_earnings"] += updated_payroll.total_earnings
        
        # Aportes patronales (Gasto para la empresa, Pasivo para el estado)
        employer_cost = (updated_payroll.ivss_employer or 0) + (updated_payroll.faov_employer or 0)
        agg_stats["total_employer_cost"] += employer_cost
        
        # Detalles de pasivos
        # IVSS Total
        ivss_total = (updated_payroll.ivss_employee or 0) + (updated_payroll.ivss_employer or 0)
        agg_stats["liability_ivss_total"] += ivss_total
        
        # FAOV Total
        faov_total = (updated_payroll.faov_employee or 0) + (updated_payroll.faov_employer or 0)
        agg_stats["liability_faov_total"] += faov_total
        
        # Otros (ISLR, etc.)
        agg_stats["liability_other_total"] += (updated_payroll.islr_retention or 0)
        
        processed_ids.append(payroll.id)
        
    await db.commit()
    
    # 3. Construir Evento Masivo
    event_payload = {
        "event": "payroll.batch_paid", # Routing key
        "tenant_id": tenant_id,
        "payment_method": request.payment_method,
        "payment_account_code": request.payment_account_code,
        "reference": request.reference or f"Nomina-Lote-{date.today()}",
        "notes": request.notes or f"Pago Lote {len(processed_ids)} Empleados",
        "paid_at": date.today().isoformat(),
        "payroll_ids": processed_ids,
        
        # Totales Financieros
        "total_net_pay": float(agg_stats["total_net_pay"]),
        "total_expense_salary": float(agg_stats["total_earnings"]),
        "total_expense_contrib": float(agg_stats["total_employer_cost"]),
        
        # Pasivos detallados
        "liability_ivss": float(agg_stats["liability_ivss_total"]),
        "liability_faov": float(agg_stats["liability_faov_total"]),
        "liability_other": float(agg_stats["liability_other_total"])
    }
    
    # # Publicar el evento único
    await publish_batch_event(event_payload)
    
    return {
        "processed": len(processed_ids),
        "total_paid": agg_stats["total_net_pay"],
        "status": "success"
    }
    
async def create_bulk_payrolls(
    db: AsyncSession,
    request: PayrollBulkCreateRequest,
    tenant_id: int
):
    """
    Genera y calcula nóminas masivamente para el periodo dado.
    Omite empleados que ya tengan nómina en ese rango de fechas.
    """
    # 1. Obtener Empleados Activos
    query = select(Employee).filter(
        Employee.tenant_id == tenant_id,
        Employee.is_active == True,
        Employee.status == "Active" 
    )
    
    # Si especificaron IDs, filtramos
    if request.employee_ids:
        query = query.filter(Employee.id.in_(request.employee_ids))
        
    result = await db.execute(query)
    employees = result.scalars().all()
    
    if not employees:
        raise ValueError("No se encontraron empleados activos para procesar.")

    created_ids = []
    skipped_count = 0
    total_estimated = Decimal(0)
    
    for emp in employees:
        # 2. Verificar duplicados (¿Ya existe nómina para este periodo?)
        # Buscamos nóminas que se solapen o sean idénticas en fechas
        existing_query = select(Payroll).filter(
            Payroll.employee_id == emp.id,
            Payroll.tenant_id == tenant_id,
            Payroll.period_start == request.period_start,
            Payroll.period_end == request.period_end,
            Payroll.status != "CANCELLED" # Ignoramos las canceladas
        )
        existing = await db.execute(existing_query)
        if existing.scalars().first():
            print(f" [!] Saltando empleado {emp.id} (Nómina ya existe)", flush=True)
            skipped_count += 1
            continue
        
        # 3. Crear el objeto Payroll (Borrador)
        new_payroll = Payroll(
            tenant_id=tenant_id,
            employee_id=emp.id,
            period_start=request.period_start,
            period_end=request.period_end,
            status="DRAFT",
            total_earnings=0,
            net_pay=0
        )
        db.add(new_payroll)
        await db.flush() # Obtener el ID
        
        # publish=False para no spamear contabilidad todavía
        calculated_payroll = await generate_payroll_event(new_payroll, db, publish=False)
        
        total_estimated += calculated_payroll.net_pay
        created_ids.append(calculated_payroll.id)
        
    await db.commit()
    
    return {
        "created": len(created_ids),
        "skipped": skipped_count,
        "total_estimated": float(total_estimated),
        "payroll_ids": created_ids
    }

async def publish_batch_event(payload: dict):
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange("erp_events", aio_pika.ExchangeType.TOPIC, durable=True)
        
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key="payroll.batch_paid"
        )
        print(f" [x] Evento de Lote Enviado: {payload['total_net_pay']} USD", flush=True)

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