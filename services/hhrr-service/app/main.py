from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud, schemas, database, models
from .schemas import PaginatedResponse
from .security import RequirePermission, Permissions, UserPayload
import pika
import json
import logging
import os

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hhrr-service")

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

def publish_event(routing_key: str, data: dict):
    try:
        url = os.getenv("RABBITMQ_URL", 'amqp://guest:guest@rabbitmq:5672/%2F')
        connection = pika.BlockingConnection(pika.URLParameters(url))
        channel = connection.channel()
        channel.exchange_declare(exchange='erp_events', exchange_type='topic', durable=True)
        
        channel.basic_publish(
            exchange='erp_events',
            routing_key=routing_key,
            body=json.dumps(data),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        logger.info(f"📢 Evento publicado: {routing_key}")
    except Exception as e:
        logger.error(f"❌ Error RabbitMQ: {e}")
        
@app.get("/access-control/check")
async def check_access(
    email: str,
    tenant_id: int,
    db: AsyncSession = Depends(database.get_db)
):
    is_allowed = await crud.check_employee_access(db, email, tenant_id)
    return {"allowed": is_allowed}

@app.get("/employees", response_model=PaginatedResponse[schemas.EmployeeResponse])
async def read_employees(
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.EMPLOYEE_READ)) 
):
    return await crud.get_employees(db, tenant_id=user.tenant_id, page=page, limit=limit)

@app.post("/employees", response_model=schemas.EmployeeResponse)
async def create_employee(
    employee: schemas.EmployeeCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.EMPLOYEE_MANAGE)) 
):
    return await crud.create_employee(db, employee, tenant_id=user.tenant_id)

@app.get("/employees/{employee_id}", response_model=schemas.EmployeeResponse)
async def read_employee(
    employee_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.EMPLOYEE_READ)) 
):
    employee = await crud.get_employee_by_id(db, employee_id, user.tenant_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return employee

@app.post("/payroll", response_model=schemas.PayrollResponse)
async def generate_payroll(
    payroll: schemas.PayrollCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PAYROLL_PROCESS)) 
):
    try:
        new_payroll = await crud.create_payroll(db, payroll, user.tenant_id)
        
        # Evento para Contabilidad
        event_data = {
            "tenant_id": user.tenant_id,
            "amount": float(new_payroll.total_amount),
            "category": "Nómina",
            "description": f"Nómina {payroll.period_start} al {payroll.period_end}",
            "reference_id": str(new_payroll.id)
        }
        publish_event("payroll.paid", event_data)
        
        return new_payroll
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# ---- NOTAS ----
@app.post("/notes", response_model=schemas.SupervisorNoteResponse)
async def create_supervisor_note(
    note: schemas.SupervisorNoteCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.EMPLOYEE_MANAGE))
):
    employee = await crud.get_employee_by_id(db, note.employee_id, user.tenant_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    return await crud.create_note(db, note, supervisor_email=user.sub, tenant_id=user.tenant_id)

@app.get("/employees/{employee_id}/notes", response_model=PaginatedResponse[schemas.SupervisorNoteResponse])
async def read_employee_notes(
    employee_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.EMPLOYEE_READ)),
    page: int = 1,
    limit: int = 10,
):
    return await crud.get_employee_notes(db, employee_id=employee_id, tenant_id=user.tenant_id, page=page, limit=limit)