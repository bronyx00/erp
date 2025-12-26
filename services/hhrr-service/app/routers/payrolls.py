from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .. import schemas
from app.database import get_db
from app.models import Payroll
from app.services.payroll_engine import create_bulk_payrolls, generate_payroll_event, process_bulk_payment
from pydantic import BaseModel
from datetime import date
from erp_common.security import RequirePermission, Permissions, UserPayload

router = APIRouter(prefix="/payrolls", tags=["Payrolls"])

class PayrollCreate(BaseModel):
    employee_id: int
    period_start: date
    period_end: date

@router.post("/", response_model=dict)
async def create_payroll(payroll_in: PayrollCreate, db: AsyncSession = Depends(get_db)):
    """Crea una nómina en borrador y la calcula inmediatamente"""
    
    # 1. Crear Objeto DB
    new_payroll = Payroll(
        employee_id=payroll_in.employee_id,
        period_start=payroll_in.period_start,
        period_end=payroll_in.period_end,
        tenant_id=1, # Debería venir del token JWT
        total_earnings=0, net_pay=0 # Se calcularán luego
    )
    db.add(new_payroll)
    await db.commit()
    await db.refresh(new_payroll)
    
    # 2. Llamar al Engine para cálculo real
    calculated_payroll = await generate_payroll_event(new_payroll, db)
    
    return {"status": "success", "payroll_id": calculated_payroll.id, "net_pay": calculated_payroll.net_pay}

@router.post("/bulk-pay", status_code=status.HTTP_200_OK)
async def bulk_pay_payrolls(
    payment_data: schemas.PayrollBulkPayRequest,
    db: AsyncSession = Depends(get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PAYROLL_PROCESS))
):
    """
    Paga múltiples nóminas y genera un solo asiento contable.
    """
    try:
        return await process_bulk_payment(db, payment_data, user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error procesando pago masivo")
    
@router.post("/generate", response_model=schemas.PayrollBulkCreateResponse)
async def generate_bulk_payrolls(
    request: schemas.PayrollBulkCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PAYROLL_PROCESS))
):
    """
    Genera (calcula) las nóminas de todos los empleados para un periodo.
    No realiza el pago ni asientos contables, solo crea los registros calculados.
    """
    try:
        return await create_bulk_payrolls(db, request, user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error generando nomina masiva: {e}")
        raise HTTPException(status_code=500, detail="Error interno generando nómina.")