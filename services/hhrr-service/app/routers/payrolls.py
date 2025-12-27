from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy import func, or_, desc, delete, cast, String
from typing import Optional
from .. import schemas
from app.database import get_db
from app.models import Payroll, Employee
from app.services.payroll_engine import create_bulk_payrolls, process_bulk_payment
from datetime import date
from erp_common.security import RequirePermission, Permissions, UserPayload

router = APIRouter(prefix="/payrolls", tags=["Payrolls"])

@router.get("/", response_model=schemas.PaginatedResponse[schemas.PayrollResponse])
async def get_payrolls(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    status: Optional[str] = None,     # Filtro opcional: 'PAID', 'DRAFT', etc.
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PAYROLL_PROCESS))
):
    """
    Obtiene el historial de nóminas con paginación, búsqueda y filtros.
    """
    offset = (page - 1) * limit
    
    stmt = select(Payroll).join(Payroll.employee)
    
    # Condiciones base
    conditions = [
        Payroll.tenant_id == user.tenant_id
    ]
    
    if status:
        conditions.append(Payroll.status == status)
    if period_start:
        conditions.append(Payroll.period_start >= period_start)
    if period_end:
        conditions.append(Payroll.period_end <= period_end)
        
    
    if search:
        search_term = f"%{search}%"
        conditions.append(
            or_(
                Employee.first_name.ilike(search_term),
                Employee.last_name.ilike(search_term),
                Employee.identification.ilike(search_term),
                cast(Payroll.id, String).ilike(search_term)
            )
        )
    
    
    
    # Conteo rápido
    count_query = select(func.count(Payroll.id)).filter(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Obtener Datos
    query = (
        stmt
        .filter(*conditions)
        .options(selectinload(Payroll.employee))
        .order_by(desc(Payroll.period_end), desc(Payroll.id))
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    data = result.scalars().all()
    
    return {
        "data": data,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if limit > 0 else 0
        }
    }

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
    
@router.post("/bulk-delete", status_code=status.HTTP_200_OK)
async def bulk_delete_payrolls(
    delete_data: schemas.PayrollBulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PAYROLL_PROCESS))
):
    """
    Elimina nóminas en estado borrador (CALCULATED o DRAFT).
    No permite eliminar nóminas PAGADAS (PAID).
    Útil para corregir errores y volver a generar.
    """
    try:
        # Ejecutamos un DELETE masivo con filtro de seguridad
        stmt = delete(Payroll).where(
            Payroll.id.in_(delete_data.payroll_ids),
            Payroll.tenant_id == user.tenant_id,
            Payroll.status != "PAID" 
        )
        
        result = await db.execute(stmt)
        await db.commit()
        
        deleted_count = result.rowcount
        
        if deleted_count == 0 and delete_data.payroll_ids:
            return {"status": "warning", "message": "No se eliminaron registros (verifique que no estén pagados).", "deleted": 0}

        return {"status": "success", "message": f"Se eliminaron {deleted_count} borradores correctamente.", "deleted": deleted_count}

    except Exception as e:
        print(f"Error borrando nóminas: {e}")
        raise HTTPException(status_code=500, detail="Error eliminando borradores.")