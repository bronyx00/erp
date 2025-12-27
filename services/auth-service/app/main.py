from fastapi import FastAPI, Depends, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
import os

from erp_common.database import DatabaseManager
from erp_common.security import get_current_user, UserPayload, RequirePermission, Permissions
from . import schemas, services, crud

DATABASE_URL = os.getenv("DATABASE_URL")
db_manager = DatabaseManager(DATABASE_URL)

app = FastAPI(title="Auth Service", root_path="/api/auth")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ENDPOINTS PÚBLICOS ---

@app.post("/register", response_model=schemas.UserResponse, status_code=201)
async def register(request: schemas.OnboardingRequest, db: AsyncSession = Depends(db_manager.get_db)):
    """Registro de Nueva Organización (Onboarding)."""
    return await services.AuthService.register_company(db, request)

@app.post("/login", response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(db_manager.get_db)):
    """Login principal con validación de horario."""
    return await services.AuthService.authenticate_user(
        db, email=form_data.username, password=form_data.password, check_schedule=True
    )

@app.post("/token", response_model=schemas.Token, include_in_schema=False)
async def login_swagger(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(db_manager.get_db)):
    """Login para Swagger (Sin chequeo de horario)."""
    return await services.AuthService.authenticate_user(
        db, email=form_data.username, password=form_data.password, check_schedule=False
    )

# --- ENDPOINTS PROTEGIDOS ---

@app.get("/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: UserPayload = Depends(get_current_user), db: AsyncSession = Depends(db_manager.get_db)):
    return await crud.get_user_by_email(db, email=current_user.sub)

@app.post("/users", response_model=schemas.UserResponse, status_code=201)
async def create_sub_user(
    user: schemas.UserCreateInternal,
    db: AsyncSession = Depends(db_manager.get_db),
    current_user: UserPayload = Depends(RequirePermission(Permissions.USER_MANAGE))
):
    return await services.AuthService.create_employee(db, user, current_user.tenant_id)

@app.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(db_manager.get_db),
    current_user: UserPayload = Depends(RequirePermission(Permissions.USER_MANAGE))
):
    """
    Desactiva un empleado y libera su correo electrónico.
    No borra el historial (facturas, nóminas siguen apuntando a su ID).
    """
    await services.AuthService.deactivate_employee(db, user_id, current_user.tenant_id)
    return

@app.get("/users", response_model=schemas.PaginatedResponse[schemas.UserResponse])
async def read_users(
    page: int = 1, limit: int = 10, search: str = None,
    db: AsyncSession = Depends(db_manager.get_db),
    current_user: UserPayload = Depends(get_current_user)
):
    return await crud.get_users(db, tenant_id=current_user.tenant_id, page=page, limit=limit, search=search)