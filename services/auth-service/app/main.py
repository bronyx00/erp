from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from . import crud, schemas, database, models
from erp_common import security
import httpx

app = FastAPI(title="Auth Service", root_path="/api/auth")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"], # Permitir Angular
    allow_credentials=True,
    allow_methods=["*"], # Permitir todos los métodos
    allow_headers=["*"], # Permitir todas las cabeceras
)

# Crear tablas al iniciar (Solo para dev)
@app.on_event("startup")
async def startup():
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

@app.post("/register", response_model=schemas.UserResponse)
async def register(user: schemas.UserCreate, db: AsyncSession = Depends(database.get_db)):
    """
    Endpoint de Registro: Crea una nueva organización y su dueño.
    """
    db_user = await crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Este Email ya está en uso")
    return await crud.register_company_and_owner(db, user_data=user)

@app.post("/login", response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(database.get_db)):
    """
    Endpoint de Login con restriccion de horario.
    """
    # Validación Credenciales
    user = await crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    
    # Validación de horario
    # Dueño siempre entra. Los demas pasan por filtro
    if user.role != "OWNER":
        try:
            async with httpx.AsyncClient() as client:
                # Llama al servicio HHRR 
                response = await client.get(
                    f"http://hhrr-service:8000/api/hhrr/access-control/check",
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
            # Si HHRR está caído, decidimos: ¿Bloquear o Dejar pasar?
            # Por seguridad en producción se suele bloquear, pero en dev warn.
            print("⚠️ Advertencia: No se pudo verificar horario con HHRR Service.")
    
    access_token = security.create_access_token(
        data={
            "sub": user.email,
            "role": user.role,
            "tenant_id": user.tenant_id
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users", response_model=schemas.UserResponse)
async def create_sub_user(
    user: schemas.SubUserCreate,
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.TokenPayload = Depends(security.get_current_user)
):
    # Verifica Permisos
    if current_user.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para crear usuarios."
        )
    # Verificar si el email ya existe
    db_user = await crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")
    
    # Crear el empleado vinculado a la misma empresa
    return await crud.create_employee(db, user, tenant_id=current_user.tenant_id)

@app.get("/users", response_model=List[schemas.UserResponse])
async def read_users(
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.TokenPayload = Depends(security.get_current_user)
):
    """
    Lista los empleados de la empresa.
    Solo permitido para OWNER y ADMIN.
    """
    if current_user.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver usuarios.")
    
    return await crud.get_users_by_tenant(db, tenant_id=current_user.tenant_id)

@app.get("/tenant/me", response_model=schemas.TenantResponse)
async def get_my_tenant(
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.TokenPayload = Depends(security.get_current_user)
):
    """Devuelve los datos de la empresa del usuario logueado"""
    result = await db.execute(select(models.Tenant).filter(models.Tenant.id == current_user.tenant_id))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return tenant