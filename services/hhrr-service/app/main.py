from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud, schemas, database, models
from .security import get_current_tenant_id

async def lifespan(app: FastAPI):
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    
app = FastAPI(title="HHRR Service", root_path="/api/hhrr", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/employees", response_model=list[schemas.EmployeeResponse])
async def read_employees(
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    return await crud.get_employees(db, tenant_id=tenant_id)

@app.post("/employees", response_model=schemas.EmployeeResponse)
async def create_employee(
    employee: schemas.EmployeeCreate,
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    return await crud.create_employee(db, employee, tenant_id=tenant_id)

@app.get("/employees/{employee_id}", response_model=schemas.EmployeeResponse)
async def read_employee(
    employee_id: int,
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    employee = await crud.get_employee_by_id(db, employee_id, tenant_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return employee