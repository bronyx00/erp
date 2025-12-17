from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import Payroll
from app.services.payroll_engine import generate_payroll_event
from pydantic import BaseModel
from datetime import date

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