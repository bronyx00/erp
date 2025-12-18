from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from erp_common import security
from . import models, schemas

# --- BÚSQUEDA BÁSICAS ---

async def get_user(db: AsyncSession, user_id: int):
    """
    Busca un usuario por su ID único.

    Args:
        db (AsyncSession): Sesión de base de datos.
        user_id (int): ID del usuario a buscar.

    Returns:
        models.User | None: El objeto usuario si existe, o None.
    """
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str):
    """
    Busca un usuario por su correo electrónico (case insensitive).
    
    Esta función es crítica para el proceso de Login.

    Args:
        db (AsyncSession): Sesión de base de datos.
        email (str): Correo electrónico.

    Returns:
        models.User | None: El objeto usuario si existe.
    """
    query = select(models.User).filter(models.User.email == email)
    result = await db.execute(query)
    return result.scalars().first()

# --- CREACIÓN BÁSICA ---

async def create_user(db: AsyncSession, user: schemas.UserCreate, tenant_id: int = None):
    """
    Registra un nuevo usuario en el sistema.
    
    Realiza automáticamente el hashing de la contraseña antes de guardar.
    Si no se especifica tenant_id (para superadmins), puede ser nulo o default.

    Args:
        db (AsyncSession): Sesión de DB.
        user (UserCreate): Datos validados del usuario (incluye password plano).
        tenant_id (int, opcional): ID de la empresa a la que pertenece.

    Returns:
        models.User: El usuario creado.
    """
    # 1. Hashear password
    hashed_password = security.get_password_hash(user.password)
    
    # 2. Crear instancia
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role,
        tenant_id=tenant_id,
        is_active=True
    )
    
    # 3. Guardar
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def create_tenant(db: AsyncSession, tenant: schemas.TenantCreate):
    """
    Crea una nueva empresa (Tenant) en el sistema.
    
    Args:
        db (AsyncSession): Sesión de DB.
        tenant (TenantCreate): Datos de la empresa (nombre, dirección, etc).

    Returns:
        models.Tenant: La empresa creada.
    """
    db_tenant = models.Tenant(**tenant.model_dump())
    db.add(db_tenant)
    await db.commit()
    await db.refresh(db_tenant)
    return db_tenant
    
# --- LÓGICA DE NEGOCIO AVANZADA ---    

async def register_company_and_owner(db: AsyncSession, user_data: schemas.UserCreate):
    """
    **Registro Maestro (Onboarding)**
    
    Realiza una transacción atómica para:
    1. Crear la Empresa (Tenant) con los datos del formulario.
    2. Crear el Usuario Dueño (Owner) vinculado a esa empresa.
    
    Args:
        db (AsyncSession): Sesión de base de datos.
        user_data (UserCreate): Datos del formulario de registro (incluye campos de empresa).

    Returns:
        models.User: El usuario dueño creado, con la relación 'tenant' cargada.
    """
    # 1. Crear el Tenant
    new_tenant = models.Tenant(
        name=user_data.company_name,
        business_name=user_data.company_business_name,
        rif=user_data.company_rif,
        address=user_data.company_address
    )
    db.add(new_tenant)
    
    # 'flush' envía los datos a la DB para generar el ID del tenant, 
    # pero NO confirma la transacción aún (si falla el usuario, se deshace todo).
    await db.flush()
    
    # 2. Crear el Usuario Owner
    hashed_pw = security.get_password_hash(user_data.password)
    new_user = models.User(
        email=user_data.email,
        hashed_password=hashed_pw,
        full_name=user_data.full_name,
        role=models.UserRole.OWNER, # Forzamos rol de Dueño
        tenant_id=new_tenant.id,
        is_active=True
    )
    db.add(new_user)
    
    # 3. Confirmar transacción completa
    await db.commit()
    
    # 4. Retornar usuario con datos de tenant para el frontend
    query = select(models.User).options(selectinload(models.User.tenant)).filter(models.User.id == new_user.id)
    result = await db.execute(query)
    return result.scalars().first()

async def create_employee(db: AsyncSession, user_data: schemas.SubUserCreate, tenant_id: int):
    """
    Crea un usuario subordinado (Empleado) vinculado a una empresa existente.
    
    Args:
        db (AsyncSession): Sesión de DB.
        user_data (SubUserCreate): Datos del empleado (email, pass, rol).
        tenant_id (int): ID de la empresa del admin que lo crea.

    Returns:
        models.User: El empleado creado.
    """
    hashed_pw = security.get_password_hash(user_data.password)
    
    new_user = models.User(
        email=user_data.email,
        hashed_password=hashed_pw,
        role=user_data.role, # El rol lo define el admin (ej. ACCOUNTANT, SALES_AGENT)
        tenant_id=tenant_id,
        is_active=True,
        full_name=user_data.full_name
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def get_users_by_tenant(db: AsyncSession, tenant_id: int):
    """
    Obtiene la lista de todos los usuarios activos de una empresa.
    """
    query = select(models.User).filter(
        models.User.tenant_id == tenant_id,
        models.User.is_active == True
    )
    result = await db.execute(query)
    return result.scalars().all()