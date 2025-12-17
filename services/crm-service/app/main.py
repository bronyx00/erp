from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud, schemas, database, models
from erp_common.security import RequirePermission, Permissions, UserPayload
from .schemas import PaginatedResponse

async def lifespan(app: FastAPI):
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    
app = FastAPI(title="CRM Service", root_path="/api/crm", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/customers", response_model=PaginatedResponse[schemas.CustomerResponse])
async def read_customers(
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.CUSTOMER_READ)) 
):
    return await crud.get_customers(db, tenant_id=user.tenant_id, page=page, limit=limit)

@app.post("/customers", response_model=schemas.CustomerResponse)
async def create_customer(
    customer: schemas.CustomerCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.CUSTOMER_CREATE)) 
):
    return await crud.create_customer(db, customer, tenant_id=user.tenant_id)