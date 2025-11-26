from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud, schemas, database, models
from .security import get_current_tenant_id

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

@app.get("balance", response_model=schemas.BalanceResponse)
async def get_balance(
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    return await crud.get_balance(db, tenant_id)