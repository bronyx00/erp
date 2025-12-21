from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud, schemas, database, models
from erp_common.security import RequirePermission, Permissions, UserPayload
from .schemas import PaginatedResponse

# Configuración de inicio
async def lifespan(app: FastAPI):
    # Crear tablas si no existen
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    
app = FastAPI(
    title="Inventory Service",
    description="Microservicio de Gestión de Inventario y Productos.",
    version="1.0.0",
    root_path="/api/inventory",
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

@app.get("/products", response_model=PaginatedResponse[schemas.ProductResponse])
async def read_products(
    page: int = 1,
    limit: int = 50,
    search: str = None,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PRODUCT_READ))   
):
    """
    **Listar Productos**
    
    Obtiene el catálogo de productos paginado.
    El filtro `search` busca por Nombre o SKU.
    """
    return await crud.get_products(db, tenant_id=user.tenant_id, page=page, limit=limit, search=search)

@app.post("/products", response_model=schemas.ProductResponse, status_code=201)
async def create_product(
    product: schemas.ProductCreate, 
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PRODUCT_CREATE)) 
):
    """
    **Crear Producto**
    
    Registra un nuevo item en el inventario.
    
    **Errores:**
    - `400 Bad Request`: Si el SKU ya existe en la empresa.
    """
    existing_prod = await crud.get_product_by_sku(db, sku=product.sku, tenant_id=user.tenant_id)
    if existing_prod:
        raise HTTPException(
            status_code=400, 
            detail=f"Ya existe un producto con el SKU '{product.sku}'"
        )
    
    return await crud.create_product(db, product, tenant_id=user.tenant_id)

@app.get("/products/{product_id}", response_model=schemas.ProductResponse)
async def read_product(
    product_id: int, 
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PRODUCT_READ)) 
):
    """Obtiene el detalle de un producto por ID."""
    db_product = await crud.get_product_by_id(db, product_id, user.tenant_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return db_product