from typing import List, Optional
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
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PRODUCT_READ))   
):
    """
    **Listar Productos**
    
    Obtiene el catálogo de productos paginado.
    El filtro `search` busca por Nombre o SKU.
    """
    return await crud.get_products(db, tenant_id=user.tenant_id, page=page, limit=limit, search=search, category=category)

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

@app.get("/categories", response_model=List[schemas.CategorySummary]) 
async def get_categories(
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PRODUCT_READ))
):
    """Obtiene lista de categorías con conteo de items."""
    return await crud.get_categories_summary(db, user.tenant_id)

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

@app.put("/products/{product_id}", response_model=schemas.ProductResponse)
async def update_product(
    product_id: int,
    product_update: schemas.ProductUpdate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PRODUCT_UPDATE)) # Asegúrate de tener este permiso
):
    """Edita un producto existente."""
    updated_product = await crud.update_product(db, product_id, product_update, user.tenant_id)
    if not updated_product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return updated_product

@app.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PRODUCT_DELETE)) 
):
    """
    **Eliminar Producto**
    
    Marca un producto como inactivo. No se borra físicamente para mantener
    la integridad de los reportes históricos.
    """
    product = await crud.delete_product(db, product_id, user.tenant_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
        
    return # 204 no devuelve cuerpo