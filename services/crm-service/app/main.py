from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud, schemas, database, models
from erp_common.security import RequirePermission, Permissions, UserPayload
from .schemas import PaginatedResponse

# Configuración de lifespan para inicializar tablas (Solo Dev)
async def lifespan(app: FastAPI):
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    
app = FastAPI(
    title="CRM Service",
    description="Microservicio de Gestión de Clientes (CRM).",
    version="1.0.0",
    root_path="/api/crm", 
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ENDPOINTS ---

@app.get("/customers", response_model=PaginatedResponse[schemas.CustomerResponse])
async def read_customers(
    page: int = 1,
    limit: int = 50,
    search: str = None,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.CUSTOMER_READ)) 
):
    """
    **Listar Clientes**
    
    Devuelve una lista paginada de clientes pertenecientes a la empresa del usuario.
    Permite filtrar por nombre, email o documento fiscal.
    """
    return await crud.get_customers(db, tenant_id=user.tenant_id, page=page, limit=limit, search=search)

@app.post("/customers", response_model=schemas.CustomerResponse, status_code=201)
async def create_customer(
    customer: schemas.CustomerCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.CUSTOMER_CREATE))
):
    """
    **Crear Cliente**
    
    Registra un nuevo cliente en el sistema.
    
    **Validaciones:**
    - Verifica si ya existe un cliente con el mismo `tax_id` (RIF/Cédula) en la empresa.
    """
    # Validación de Negocio: Evitar duplicados por Documento Fiscal
    if customer.tax_id:
        existing_customer = await crud.get_customer_by_tax_id(db, user.tenant_id, customer.tax_id)
        if existing_customer:
            raise HTTPException(
                status_code=400, 
                detail=f"Ya existe un cliente registrado con el documento {customer.tax_id}"
            )

    return await crud.create_customer(db, customer=customer, tenant_id=user.tenant_id)