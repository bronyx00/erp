from typing import List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import pika
import json
import logging
import os

from . import crud, schemas, database, models
from .schemas import PaginatedResponse
from erp_common.security import RequirePermission, Permissions, UserPayload
from app.routers import payrolls


# Configuración de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hhrr-service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    
app = FastAPI(
    title="HHRR Service",
    description="Microservicio de Recursos Humanos: Empleados, Asistencia y Nómina.",
    version="1.0.0",
    root_path="/api/hhrr",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    await database.init_db()
    
# Router adicional
app.include_router(payrolls.router)

# --- ENDPOINTS GENERALES ---

@app.get("/health")
def health_check():
    """Health check para Kubernetes/Docker."""
    return {"status": "ok"}
        
@app.get("/access-control/check")
async def check_access(
    email: str,
    tenant_id: int,
    db: AsyncSession = Depends(database.get_db)
):
    """
    **Verificar Acceso (Control de Horario)**
    
    Endpoint interno consultado por `auth-service`.
    Retorna `allowed: True` si el empleado puede entrar al sistema a esta hora.
    """
    is_allowed = await crud.check_employee_access(db, email, tenant_id)
    return {"allowed": is_allowed}

# --- GESTIÓN DE EMPLEADOS ---

@app.get("/employees", response_model=PaginatedResponse[schemas.EmployeeResponse])
async def read_employees(
    page: int = 1,
    limit: int = 50,
    search: str = None,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.EMPLOYEE_READ)) 
):
    """Lista todos los empleados de la empresa."""
    return await crud.get_employees(db, tenant_id=user.tenant_id, page=page, limit=limit, search=search)

@app.post("/employees", response_model=schemas.EmployeeResponse)
async def create_employee(
    employee: schemas.EmployeeCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.EMPLOYEE_MANAGE)) 
):
    """Registra un nuevo empleado."""
    return await crud.create_employee(db, employee, tenant_id=user.tenant_id)

@app.get("/employees/{employee_id}", response_model=schemas.EmployeeResponse)
async def read_employee(
    employee_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.EMPLOYEE_READ)) 
):
    """Obtiene el detalle completo de un empleado."""
    employee = await crud.get_employee_by_id(db, employee_id, user.tenant_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return employee

@app.put("/employees/{employee_id}", response_model=schemas.EmployeeResponse)
async def update_employee(
    employee_id: int,
    employee_update: schemas.EmployeeUpdate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.EMPLOYEE_MANAGE))
):
    """Actualiza datos del empleado."""
    updated_employee = await crud.update_employee(db, employee_id, employee_update, user.tenant_id)
    if not update_employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return updated_employee
    
# --- NOTAS DE SUPERVISOR ---

@app.post("/notes", response_model=schemas.SupervisorNoteResponse)
async def create_supervisor_note(
    note: schemas.SupervisorNoteCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.EMPLOYEE_MANAGE))
):
    """Añade una nota al expediente del empleado."""
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
    """Lee las notas asociadas a un empleado."""
    return await crud.get_employee_notes(db, employee_id=employee_id, tenant_id=user.tenant_id, page=page, limit=limit)

# --- HORARIOS ---

@app.post("/work-schedules", response_model=schemas.WorkScheduleResponse)
async def create_work_schedule(
    schedule: schemas.WorkScheduleCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.EMPLOYEE_MANAGE))
):
    """Crea un nuevo esquema de horario laboral."""
    return await crud.create_schedule(db, schedule, user.tenant_id)

@app.get("/work-schedules", response_model=List[schemas.WorkScheduleResponse])
async def read_work_schedules(
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.EMPLOYEE_READ))
):
    """Lista todos los horarios disponibles."""
    return await crud.get_schedule(db, user.tenant_id)

# --- UTILIDADES RABBITMQ ---
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