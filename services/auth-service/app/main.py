from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta
from typing import List
import httpx
import os

# Importaciones de erp_common
from erp_common.database import DatabaseManager
from erp_common import security
from erp_common.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES, 
    create_access_token, 
    get_current_user, 
    UserPayload 
)

# Importaciones locales
from . import crud, models, schemas

# Configuración de Base de Datos
DATABASE_URL = os.getenv("DATABASE_URL")
db_manager = DatabaseManager(DATABASE_URL)

app = FastAPI(
    title="Auth Service",
    description="Microservicio encargado de la autenticación, gestión de usuarios y empresas (tenants).",
    version="1.0.0",
    root_path="/api/auth"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Eventos de inicio (Crear tablas si no existen)
async def startup():
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
        
# --- ENDPOINTS PÚBLICOS ---

@app.post("/register", response_model=schemas.UserResponse, status_code=201)
async def register(
    user: schemas.UserCreate, 
    db: AsyncSession = Depends(db_manager.get_db)
):
    """
    **Registro de Nueva Organización (Onboarding)**
    
    Este endpoint se usa en la pantalla de "Regístrate" pública.
    Crea una nueva empresa (Tenant) y al usuario que la solicita como DUEÑO (Owner).
    """
    db_user = await crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Este correo electrónico ya está en uso.")
    
    return await crud.register_company_and_owner(db, user_data=user)

@app.post("/login", response_model=schemas.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(db_manager.get_db)
):
    """
    **Inicio de Sesión Principal (Login App)**
    
    Autentica al usuario y verifica restricciones horarias con RRHH.
    
    **Flujo:**
    1. Valida credenciales.
    2. Si NO es OWNER, consulta a `hhrr-service` si el usuario tiene permitido entrar a esta hora.
    3. Genera y retorna el Token JWT.
    """
    # 1. Validación Credenciales
    user = await crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401, 
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    # 2. Validación de Horario Laboral
    if user.role != "OWNER":
        try:
            # Comunicación interna entre contenedores
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://hhrr-service:8000/api/hhrr/access-control/check",
                    params={"email": user.email, "tenant_id": user.tenant_id},
                    timeout=3.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("allowed") is False:
                        raise HTTPException(
                            status_code=403,
                            detail="Acceso denegado: Estás fuera de tu horario laboral."
                        )
        except httpx.RequestError:
            # Fail-open (permitir) o Fail-close (bloquear) si HHRR falla. 
            # Aquí elegimos advertir pero permitir entrar al sistema (Fail-open).
            print(f"⚠️ Advertencia: No se pudo verificar horario para {user.email}. HHRR Service inalcanzable.")

    # 3. Generar Token
    access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = create_access_token(
        data={
            "sub": user.email,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "user_id": user.id
        },
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=schemas.Token)
async def login_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(db_manager.get_db)
):
    """
    **Login para Swagger UI**
    
    Valida las credenciales (email y password) y emite un JWT (JSON Web Token).
    Igual que `/login` pero sin la validación de horario estricta. 
    Se mantiene para compatibilidad con el botón 'Authorize' de la documentación automática.
    
    - **username**: El correo electrónico del usuario.
    - **password**: La contraseña en texto plano.
    
    **Retorna:**
    - `access_token`: Token para usar en los headers `Authorization: Bearer ...`
    - `token_type`: Siempre "bearer".
    """
    # Reutilizamos la lógica, podríamos simplemente llamar a la función login si quisiéramos validar horario también aquí.
    user = await crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "tenant_id": user.tenant_id, "user_id": user.id}
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- ENDPOINTS PROTEGIDOS ---

@app.get("/me", response_model=schemas.UserResponse)
async def read_users_me(
    current_user: UserPayload = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_db)
):
    """
    **Perfil de Usuario**
    
    Retorna la información del usuario autenticado actual.
    """
    user = await crud.get_user_by_email(db, email=current_user.sub)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

@app.get("/tenant/me", response_model=schemas.TenantResponse)
async def get_my_tenant(
    db: AsyncSession = Depends(db_manager.get_db),
    current_user: UserPayload = Depends(get_current_user)
):
    """
    **Datos de la Empresa**
    
    Retorna la información fiscal y configuración de la empresa a la que pertenece el usuario.
    """
    query = select(models.Tenant).filter(models.Tenant.id == current_user.tenant_id)
    result = await db.execute(query)
    tenant = result.scalars().first()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return tenant

@app.post("/users", response_model=schemas.UserResponse, status_code=201)
async def create_sub_user(
    user: schemas.SubUserCreate,
    db: AsyncSession = Depends(db_manager.get_db),
    current_user: UserPayload = Depends(get_current_user)
):
    """
    **Crear Empleado (Sub-usuario)**
    
    Permite a un OWNER o ADMIN registrar un nuevo empleado en su misma empresa.
    """
    # 1. Verificar Permisos
    if current_user.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="No tienes permisos para crear usuarios.")
    
    # 2. Verificar duplicidad
    db_user = await crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")
    
    # 3. Crear empleado vinculado
    return await crud.create_employee(db, user, tenant_id=current_user.tenant_id)

@app.get("/users", response_model=List[schemas.UserResponse])
async def read_users(
    db: AsyncSession = Depends(db_manager.get_db),
    current_user: UserPayload = Depends(get_current_user)
):
    """
    **Listar Empleados**
    
    Devuelve la lista de todos los usuarios activos que pertenecen a la empresa.
    """
    if current_user.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver el listado de usuarios.")
    
    return await crud.get_users_by_tenant(db, tenant_id=current_user.tenant_id)