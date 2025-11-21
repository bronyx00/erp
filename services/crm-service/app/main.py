from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud, schemas, database, models
from .security import get_current_user_email

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

@app.get("/customers", response_model=list[schemas.CustomerResponse])
async def read_customers(
    db: AsyncSession = Depends(database.get_db),
    current_user: str = Depends(get_current_user_email)
):
    return await crud.get_customers(db, owner_email=current_user)

@app.post("/customers", response_model=schemas.CustomerResponse)
async def create_customer(
    customer: schemas.CustomerCreate,
    db: AsyncSession = Depends(database.get_db),
    current_user: str = Depends(get_current_user_email)
):
    return await crud.create_customer(db, customer, owner_email=current_user)