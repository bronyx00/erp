from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
from . import models, schemas

async def get_customers(
    db: AsyncSession, 
    tenant_id: int, 
    page: int = 1, 
    limit: int = 50, 
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Obtiene el listado paginado de clientes de una empresa.

    Optimizado para contar IDs en lugar de filas completas.

    Args:
        db (AsyncSession): Sesión de base de datos.
        tenant_id (int): ID de la empresa.
        page (int): Número de página.
        limit (int): Registros por página.
        search (str, optional): Filtro por nombre, email o documento fiscal.

    Returns:
        Dict: Estructura con 'data' (lista) y 'meta' (paginación).
    """
    offset = (page - 1) * limit
    
    # Condiciones base (Multi-tenancy seguro)
    conditions = [
        models.Customer.tenant_id == tenant_id, 
        models.Customer.is_active == True
    ]
    
    if search:
        search_term = f"%{search}%"
        conditions.append(
            or_(
                models.Customer.name.ilike(search_term),
                models.Customer.email.ilike(search_term),
                models.Customer.tax_id.ilike(search_term)
            )
        )

    # 1. Conteo Rápido (Count ID)
    count_query = select(func.count(models.Customer.id)).filter(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 2. Obtener Datos
    query = (
        select(models.Customer)
        .filter(*conditions)
        .order_by(models.Customer.name.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    data = result.scalars().all()
    
    # Cálculo seguro de páginas
    total_pages = (total + limit - 1) // limit if limit > 0 else 0
    
    return {
        "data": data,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    }

async def get_customer_by_tax_id(db: AsyncSession, tenant_id: int, tax_id: str):
    """Busca un cliente por su documento fiscal dentro de la misma empresa."""
    query = select(models.Customer).filter(
        models.Customer.tenant_id == tenant_id,
        models.Customer.tax_id == tax_id
    )
    result = await db.execute(query)
    return result.scalars().first()

async def create_customer(
    db: AsyncSession, 
    customer: schemas.CustomerCreate, 
    tenant_id: int
) -> models.Customer:
    """
    Registra un nuevo cliente en el CRM.

    Args:
        db (AsyncSession): Sesión DB.
        customer (CustomerCreate): Datos del cliente.
        tenant_id (int): Empresa dueña del registro.

    Returns:
        models.Customer: Cliente creado.
    """
    db_customer = models.Customer(
        **customer.model_dump(),
        tenant_id=tenant_id
    )
    db.add(db_customer)
    await db.commit()
    await db.refresh(db_customer)
    return db_customer