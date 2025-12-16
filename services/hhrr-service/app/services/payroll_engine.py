import json
import os
import aio_pika
from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Employee, Payroll

# RabbitMQ Connection URL
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

class VenezuelanPayrollCalculator:
    """
    Motor para calcular deducciones y contribuciones legales venezolanas.
    """
    
    # Constantes de Ley
    IVSS_EMP_RATE = Decimal("0.04")  # 4% Empleado
    IVSS_COMP_RATE = Decimal("0.09") # 9% Patrono (Riesgo Mínimo)
    FAOV_EMP_RATE = Decimal("0.01")  # 1% Empleado
    FAOV_COMP_RATE = Decimal("0.02") # 2% Patrono
    
    # Tope de Salarios Mínimo
    IVSS_CAP_MULTIPLIER = 5 
    MINIMUM_WAGE = Decimal("130.00")
    
    @staticmethod
    def calculate_deductions(salary: Decimal):
        """
        Calcula valores distintos para las deducciones.
        """
        ivss_emp = salary * VenezuelanPayrollCalculator.IVSS_EMP_RATE
        faov_emp = salary * VenezuelanPayrollCalculator.FAOV_EMP_RATE
        
        # Costo de la Empresa
        ivss_comp = salary * VenezuelanPayrollCalculator.IVSS_COMP_RATE
        faov_comp = salary * VenezuelanPayrollCalculator.FAOV_COMP_RATE
        
        return {
            "ivss_employee": round(ivss_emp, 2),
            "faov_employee": round(faov_emp, 2),
            "ivss_employer": round(ivss_comp, 2),
            "faov_employer": round(faov_comp, 2)
        }

async def generate_payroll_event(payroll: Payroll, db: AsyncSession):
    """
    1. Calcula valores según el salario del empleado.
    2. Guarda la nómina actualizada en la base de datos.
    3. Publica el evento 'payroll.calculated' en RabbitMQ.
    """
    
    # Obtener Datos del Empleado
    employee = await db.get(Employee, payroll.employee_id)
    if not employee:
        raise ValueError("Empleado no encontrado")
    
    salary = Decimal(str(employee.salary)) if employee.salary else Decimal("0.00")
    
    # Ejecutar calculos de ley
    calcs = VenezuelanPayrollCalculator.calculate_deductions(salary)
    
    # Actualiza objeto de nómina
    payroll.base_salary = salary
    payroll.total_earnings = salary # + bonuses if any
    
    payroll.ivss_employee = calcs["ivss_employee"]
    payroll.faov_employee = calcs["faov_employee"]
    payroll.ivss_employer = calcs["ivss_employer"]
    payroll.faov_employer = calcs["faov_employer"]
    
    # Marcador de posición ISLR simple
    payroll.islr_retention = Decimal("0.00")
    
    payroll.total_deductions = payroll.ivss_employee + payroll.faov_employee + payroll.islr_retention
    payroll.net_pay = payroll.total_earnings - payroll.total_deductions
    payroll.status = "CALCULATED"
    
    db.add(payroll)
    await db.commit()
    await db.refresh(payroll)
    
    # Enviar evento a Contabilidad
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
            
            # Datos financieros (Convertir decimales a cadenas/flotantes para JSON)
            "total_earnings": float(payroll.total_earnings),
            "ivss_employee": float(payroll.ivss_employee),
            "faov_employee": float(payroll.faov_employee),
            "islr_retention": float(payroll.islr_retention),
            
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
        print(f" [x] Sent Payroll Event #{payroll.id} to Accounting", flush=True)