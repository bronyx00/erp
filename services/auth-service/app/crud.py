from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, or_
from . import models

# --- LECTURA ---
async def get_user_by_email(db: AsyncSession, email: str):
    query = (
        select(models.User)
        .options(selectinload(models.User.tenant))
        .filter(models.User.email == email)
    )
    result = await db.execute(query)
    return result.scalars().first()

async def get_user_by_id(db: AsyncSession, user_id: int):
    """Busca un usuario por ID."""
    query = (
        select(models.User)
        .options(selectinload(models.User.tenant))
        .filter(models.User.id == user_id)
    )
    result = await db.execute(query)
    return result.scalars().first()

async def get_users(
    db: AsyncSession, 
    tenant_id: int,
    page: int = 1,
    limit: int = 30,
    search: str = None
):
    offset = (page - 1) * limit
    
    # Condiciones
    conditions = [
        models.User.tenant_id == tenant_id,
        models.User.is_active == True
    ]
    
    # Filtro de busqueda
    if search:
        search_term = f"%{search}%"
        conditions.append(
            or_(
                models.User.full_name.ilike(search_term),
                models.User.email.ilike(search_term)
            )
        )
        
    # 1. Contar total de registros 
    count_query = select(func.count(models.User.id)).filter(*conditions)
    total = (await db.execute(count_query)).scalar() or 0
    
    # 2. Obtener datos paginados
    query = (
        select(models.User)
        .options(selectinload(models.User.tenant)) # Carga la relación tenant
        .filter(*conditions)
        .order_by(models.User.full_name.asc())     # Orden alfabético
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    users = result.scalars().all()
    
    # 3. Retornar estructura completa
    return {
        "data": users,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if limit > 0 else 0
        }
    }


# --- ESCRITURA ---
async def create_tenant(db: AsyncSession, tenant_data: dict):
    db_tenant = models.Tenant(**tenant_data)
    db.add(db_tenant)
    await db.flush() # flush para obtener ID sin commit final aun
    return db_tenant

async def create_user(db: AsyncSession, user_data: dict):
    """Crea un usuario genérico (Dueño o Empleado)."""
    db_user = models.User(**user_data)
    db.add(db_user)
    await db.commit()
    
    query = select(models.User).options(selectinload(models.User.tenant)).filter(models.User.id == db_user.id)
    result = await db.execute(query)
    
    return result.scalars().first()

async def create_tenant_with_owner(db: AsyncSession, tenant_obj: models.Tenant, user_obj: models.User):
    """Transacción atómica para onboarding."""
    db.add(tenant_obj)
    await db.flush() # Genera ID del tenant
    
    user_obj.tenant_id = tenant_obj.id
    db.add(user_obj)
    await db.commit()
    
    # Recargar con relación
    query = select(models.User).options(selectinload(models.User.tenant)).filter(models.User.id == user_obj.id)
    return (await db.execute(query)).scalars().first()

async def archive_user(db: AsyncSession, user: models.User):
    """
    Desactiva al usuario y libera su email para que pueda ser reutilizado.
    """
    import time
    # Cambiamos el email a algo único para liberar el original
    # Ej: juan@test.com -> juan@test.com.archived.17098234
    user.email = f"{user.email}.archived.{int(time.time())}"
    user.is_active = False
    
    db.add(user)
    await db.commit()
    
    query = select(models.User).options(selectinload(models.User.tenant)).filter(models.User.id == user.id)
    result = await db.execute(query)
    return result.scalars().first()

async def deactivate_user_by_email(db: AsyncSession, email: str, tenant_id: int):
    """
    Desactiva un usuario buscando por email y tenant.
    Usado para sincronización automática desde RRHH.
    """
    user = await get_user_by_email(db, email)
    
    if not user:
        return None # No existe usuario para ese empleado, no hacemos nada
        
    if user.tenant_id != tenant_id:
        return None # Seguridad: No tocar usuarios de otros tenants
        
    # Reutilizamos la lógica de archivar
    return await archive_user(db, user)