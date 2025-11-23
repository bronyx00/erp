from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud, schemas, security, database, models

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
    Endpoint de Login: Devuelve un JWT enriquecido con rol y tenand_id.
    """
    user = await crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    
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