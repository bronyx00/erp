from datetime import date
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.future import select
from sqlalchemy import func, insert
import pandas as pd
import io
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud, schemas, database, models
from .security import get_current_tenant_id
from .schemas import PaginatedResponse

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
    return await crud.create_transaction(db, transaction, tenant_id)

@app.get("/balance", response_model=schemas.BalanceResponse)
async def get_balance(
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    return await crud.get_balance(db, tenant_id)

@app.post("/accounts/import", response_model=schemas.ImportResult)
async def import_chart_of_accounts(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Importa Plan de Cuentas desde Excel"""
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
    db: AsyncSession = Depends(database.get_db)
):
    """Libro Diario: Lista cronológicamente de todos los asientos"""
    offset = (page - 1) * limit
    
    base_query = (
        select(models.LedgerEntry)
        .filter(
            models.LedgerEntry.transaction_date >= start_date,
            models.LedgerEntry.transaction_date <= end_date
        )
    )
    
    # Total Count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0
    
    # Fetch Data 
    query = (
        base_query
        .options(selectinload(models.LedgerEntry.lines).joinedload(models.LedgerLine.account))
        .order_by(models.LedgerEntry.transaction_date, models.LedgerEntry.id)
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    total_pages = (total + limit - 1) // limit
    
    return {
        "data": entries,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    }

@app.get("/books/ledger")
async def get_generatl_ledger(
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Libro Mayor: Balance agrupado por cuenta"""
    query = (
        select(
            models.Account.code,
            models.Account.name,
            func.sum(models.LedgerLine.debit).label('total_debit'),
            func.sum(models.LedgerLine.credit).label('total_credit')
        )
        .filter(models.Account.tenant_id == tenant_id)
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