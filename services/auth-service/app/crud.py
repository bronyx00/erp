from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from . import models, schemas
from erp_common import security

async def get_user_by_email(db: AsyncSession, email: str):
    """Busca un usuario por email"""
    query = select(models.User).options(selectinload(models.User.tenant)).filter(models.User.email == email)
    result = await db.execute(query)
    return result.scalars().first()

async def register_company_and_owner(db: AsyncSession, user_data: schemas.UserCreate):
    """
    Crea una nueva EMPRESA y su usuario DUEÑO en una sola transacción.
    """
    # Crea el objeto Tenant
    new_tenant = models.Tenant(
        name=user_data.company_name,
        business_name=user_data.company_business_name,
        rif=user_data.company_rif,
        address=user_data.company_address
    )
    db.add(new_tenant)
    
    # Flush para que la DB asigne el ID al tenant sin cerrar la transacción
    await db.flush()
    
    # Crea el Usuario Owner vinculado al Tenant
    hashed_pw = security.get_password_hash(user_data.password)
    new_user = models.User(
        email=user_data.email,
        hashed_password=hashed_pw,
        role=models.UserRole.OWNER, # Rol por defecto al registrarse
        tenant_id=new_tenant.id
    )
    db.add(new_user)
    
    # Confirmar todo
    await db.commit()
    
    query = select(models.User).options(selectinload(models.User.tenant)).filter(models.User.id == new_user.id)
    result = await db.execute(query)
    created_user = result.scalars().first()

    return created_user

async def create_employee(db: AsyncSession, user_data: schemas.SubUserCreate, tenant_id: int):
    hashed_pw = security.get_password_hash(user_data.password)
    
    new_user = models.User(
        email=user_data.email,
        hashed_password=hashed_pw,
        role=user_data.role,
        tenant_id=tenant_id,
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    
    query = select(models.User).options(selectinload(models.User.tenant)).filter(models.User.id == new_user.id)
    result = await db.execute(query)
    return result.scalars().first()

async def get_users_by_tenant(db: AsyncSession, tenant_id: int):
    """Devuelve todos los usuarios que pertenecen a una empresa."""
    query = select(models.User).filter(
        models.User.tenant_id == tenant_id,
        models.User.is_active == True
    )
    result = await db.execute(query)
    return result.scalars().all()

