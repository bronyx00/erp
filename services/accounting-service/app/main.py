from datetime import date, timedelta
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from contextlib import asynccontextmanager
from sqlalchemy import func, insert
import pandas as pd
import io
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud, schemas, database, models
from erp_common.security import RequirePermission, Permissions, UserPayload, oauth2_scheme, get_current_tenant_id
from .schemas import PaginatedResponse
from .utils.financial_pdf import FinancialReportGenerator

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    
app = FastAPI(title="Accounting Service", root_path="/api/accounting", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/transactions", response_model=schemas.TransactionResponse)
async def create_expense(
    transaction: schemas.TransactionCreate,
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Registra una transacción manual (ingreso o egreso).
    
    Se utiliza principalmente para registrar gastos operativos o ingresos 
    que no provienen de facturación automática.
    """
    return await crud.create_transaction(db, transaction, tenant_id)

@app.get("/balance", response_model=schemas.BalanceResponse)
async def get_balance(
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Obtiene un resumen financiero rápido.
    
    Retorna la suma total de ingresos, egresos y la utilidad neta calculada
    en base a todas las transacciones registradas.
    """
    return await crud.get_balance(db, tenant_id)

@app.post("/accounts/import", response_model=schemas.ImportResult)
async def import_chart_of_accounts(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Carga masiva del Plan de Cuentas desde un archivo Excel (.xlsx).
    
    El archivo debe contener las columnas obligatorias:
    - `codigo`: Código contable (ej. 1.1.01)
    - `nombre`: Nombre de la cuenta
    - `tipo`: Tipo de cuenta (ASSET, LIABILITY, EQUITY, INCOME, EXPENSE)
    """
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(400, "Solo se permiten archivos Excel (.xlsx)")
    
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        df.columns = [c.lower() for c in df.columns]
        
        required = ['codigo', 'nombre', 'tipo']
        if not required.issubset(df.columns):
            raise HTTPException(400, f"Columnas requeridas: f{required}")
        
        tenant_id = tenant_id
        
        # Convierte DataFrame a lista de Diccionarios para SQLAlchemy Core
        accounts_data = []
        for _, row in df.iterrows():
            accounts_data.append({
                "tenant_id": tenant_id,
                "code": str(row['codigo']),
                "name": row['nombre'],
                "account_type": row['tipo'].upper(),
                "is_transactional": True,
                "level": len(str(row['codigo']).split('.')),
                "is_active": True,
                "balance": 0
            })
            
        if accounts_data:
            stmt = insert(models.Account).values(accounts_data)
            
            await db.on_conflict_do_nothing()
            await db.execute(stmt)
            await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, f"Error procesando archivo: {str(e)}")
            
    
@app.post("/accounts/seed-puc-ve")
async def trigger_seed_puc(
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Carga el PUC Venezolano Completo"""
    from app.seed_puc_ve import seed_puc
    await seed_puc(tenant_id=tenant_id)
    return {"message": "PUC Venezuela iniciado"}

# --- ENDPOINTS DE LIBROS CONTABLES ---

@app.get("/books/journal", response_model=PaginatedResponse[schemas.LedgerEntryResponse])
async def get_journal_book(   
    start_date: date,
    end_date: date,
    page: int = 1,
    limit: int = 100,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.ACCOUNTING_MANAGE)) 
):
    """Libro Diario: Lista cronológicamente de todos los asientos"""
    offset = (page - 1) * limit
    conditions = [
        models.LedgerEntry.tenant_id == user.tenant.id, 
        models.LedgerEntry.transaction_date >= start_date, 
        models.LedgerEntry.transaction_date <= end_date
        ]
    
    # Conteo rapido
    count_query = select(func.count(models.LedgerEntry)).filter(*conditions)
    total = (await db.execute(count_query)).scalar() or 0
    
    query = (
        select(models.LedgerEntry)
        .filter(*conditions)
        .order_by(models.LedgerEntry.transaction_date, models.LedgerEntry.id)
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    
    return {
        "data": result.scalars().all(),
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if limit > 0 else 0
        }
    }

@app.get("/books/ledger")
async def get_general_ledger(
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.ACCOUNTING_MANAGE))
):
    """Libro Mayor: Balance agrupado por cuenta"""
    query = (
        select(
            models.Account.code,
            models.Account.name,
            func.sum(models.LedgerLine.debit).label('total_debit'),
            func.sum(models.LedgerLine.credit).label('total_credit')
        )
        .filter(models.Account.tenant_id == user.tenant_id)
        .join(models.LedgerLine, models.Account.id == models.LedgerLine.account_id)
        .group_by(models.Account.id)
    )
    
    result = await db.execute(query)
    
    ledger = []
    
    for row in result:
        balance = row.total_debit - row.total_credit
        
        ledger.append({
            "code": row.code,
            "account": row.name,
            "debit": row.total_debit,
            "credit": row.total_credit,
            "balance": balance
        })
    
    return ledger

@app.get("/reports/download")
async def download_financial_report(
    report_type: str, # 'balance_sheet', 'income_statement', 'equity_changes', 'clear'
    period: str,        # 'Q1', 'Q2', 'Q3', 'Q4', 'S1', 'S2', 'YEAR'
    year: int,
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    token: str = Depends(oauth2_scheme)
):
    """
    Genera y descarga reportes financieros en formato PDF.
    
    - **report_type**: 'balance_sheet' (Balance General), 'income_statement' (Estado de Resultados), etc.
    - **period**: Trimestre (Q1-Q4), Semestre (S1-S2) o Año (YEAR).
    - **year**: Año fiscal del reporte.
    
    Retorna un archivo PDF (application/pdf).
    """
    # Obtener Datos de Empresa
    tenant_info = await crud.get_tenant_data(token)
    company_name = tenant_info.get('business_name') if tenant_info else "EMPRESA DEMO"
    rif = tenant_info.get('rif') if tenant_info else "J-00000000-0"
    
    
    # Denifir Fechas segun periodo
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    if period == 'Q1':
        end_date = date(year, 3, 31)
    elif period == 'Q2':
        start_date = date(year, 4, 1); end_date = date(year, 6, 30)
    elif period == 'Q3':
        start_date = date(year, 7, 1); end_date = date(year, 9, 30)
    elif period == 'Q4':
        start_date = date(year, 10, 1); end_date = date(year, 12, 31)
    elif period == 'S1':
        end_date = date(year, 6, 30)
    elif period == 'S2':
        start_date = date(year, 7, 1); end_date = date(year, 12, 31)
        
    # Obtener Datos
    data = await crud.get_account_balances(db, tenant_id, start_date, end_date)
    
    generator = FinancialReportGenerator(company_name, rif)
    filename = f"{tenant_info.get('name')}_{report_type}_{period}_{year}.pdf"
    
    if report_type == 'balance_sheet':
        # Para Balance: Saldos Acumulados a la fecha de fin
        data = await crud.get_account_balances_at_date(db, tenant_id, end_date)
        pdf = generator.generate_balance_sheet(data, end_date)
        
    elif report_type == 'income_statement':
        # Para Resultados: Movimientos del periodo
        data = await crud.get_period_movements(db, tenant_id, start_date, end_date)
        pdf = generator.generate_income_statement(data, start_date, end_date)
        
    elif report_type == 'equity_changes':
        # Para Patrimonio: Saldos acumulados
        data = await crud.get_account_balances_at_date(db, tenant_id, end_date)
        pdf = generator.generate_equity_changes(data, start_date, end_date)
        
    elif report_type == 'cash_flow':
        # Para Flujo de Efectivo: Necesitamos AMBOS (Saldos para Activos/Pasivos y Movimientos para Utilidad)
        balance_data = await crud.get_account_balances_at_date(db, tenant_id, end_date)
        income_data = await crud.get_period_movements(db, tenant_id, start_date, end_date)
        pdf = generator.generate_cash_flow(balance_data, income_data, start_date, end_date)
        
    else:
        raise HTTPException(400, "Tipo de reporte no válido")
    
    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )