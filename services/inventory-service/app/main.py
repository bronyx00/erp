from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud, schemas, database, models
from .security import get_current_tenant_id
from .schemas import PaginatedResponse

# Inicialización de DB
async def lifespan(app: FastAPI):
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    
app = FastAPI(title="Inventory Service", root_path="/api/inventory", lifespan=lifespan)

# Configuración CORS}
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/products", response_model=PaginatedResponse[schemas.ProductResponse])
async def read_products(
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id)    
):
    return await crud.get_products(db, tenant_id=tenant_id, page=page, limit=limit)

@app.post("/products", response_model=schemas.ProductResponse)
async def create_product(
    product: schemas.ProductCreate, 
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    # Añadir validacion si el sku ya existe
    return await crud.create_product(db, product, tenant_id=tenant_id)

@app.get("/products/{product_id}", response_model=schemas.ProductResponse)
async def read_product(
    product_id: int, 
    db: AsyncSession = Depends(database.get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    db_product = await crud.get_product_by_id(db, product_id, tenant_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return db_product