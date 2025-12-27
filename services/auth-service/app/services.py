import httpx
import os
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from erp_common import security
from . import crud, models, schemas

HHRR_SERVICE_URL = os.getenv("HHRR_SERVICE_URL", "http://hhrr-service:8000")

class AuthService:
    
    @staticmethod
    async def register_company(db: AsyncSession, data: schemas.OnboardingRequest):
        # 1. Verificar duplicados
        if await crud.get_user_by_email(db, email=data.email):
            raise HTTPException(status_code=400, detail="El email ya está registrado.")
            
        # 2. Preparar objetos
        tenant_data = models.Tenant(
            name=data.company_name,
            business_name=data.company_business_name,
            rif=data.company_rif,
            address=data.company_address
        )
        
        hashed_pw = security.get_password_hash(data.password)
        user_data = models.User(
            email=data.email,
            hashed_password=hashed_pw,
            full_name=data.full_name,
            role=models.UserRole.OWNER.value,
            is_active=True
        )
        
        # 3. Guardar transacción
        return await crud.create_tenant_with_owner(db, tenant_data, user_data)

    @staticmethod
    async def create_employee(db: AsyncSession, data: schemas.UserCreateInternal, tenant_id: int):
        if await crud.get_user_by_email(db, data.email):
            raise HTTPException(status_code=400, detail="El email ya está registrado.")
            
        hashed_pw = security.get_password_hash(data.password)
        
        user_dict = {
            "email": data.email,
            "hashed_password": hashed_pw,
            "full_name": data.full_name,
            "role": data.role.value,
            "tenant_id": tenant_id,
            "is_active": True
        }
        
        return await crud.create_user(db, user_dict)

    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str, check_schedule: bool = True):
        # 1. Validar Credenciales
        user = await crud.get_user_by_email(db, email)
        if not user or not security.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 2. Validar Horario con RRHH (Si no es Owner)
        if check_schedule and user.role != models.UserRole.OWNER.value:
            await AuthService._check_hhrr_access(user.email, user.tenant_id)
            
        # 3. Generar Token
        access_token = security.create_access_token(
            data={
                "sub": user.email,
                "role": user.role,
                "tenant_id": user.tenant_id,
                "user_id": user.id
            },
            expires_delta=timedelta(minutes=int(security.ACCESS_TOKEN_EXPIRE_MINUTES))
        )
        return {"access_token": access_token, "token_type": "bearer"}

    @staticmethod
    async def _check_hhrr_access(email: str, tenant_id: int):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{HHRR_SERVICE_URL}/api/hhrr/access-control/check",
                    params={"email": email, "tenant_id": tenant_id},
                    timeout=3.0
                )
                if response.status_code == 200 and response.json().get("allowed") is False:
                    raise HTTPException(status_code=403, detail="Acceso denegado: Fuera de horario laboral.")
        except httpx.RequestError:
            print(f"⚠️ Warning: HHRR Service inalcanzable. Fail-open.")
            
    @staticmethod
    async def deactivate_employee(db: AsyncSession, user_id: int, current_tenant_id: int):
        # 1. Buscar usuario
        user = await crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
        # 2. Verificar que pertenece a MI empresa (Seguridad)
        if user.tenant_id != current_tenant_id:
            raise HTTPException(status_code=403, detail="No puedes eliminar usuarios de otra organización.")
            
        # 3. Evitar borrar al Dueño (OWNER)
        if user.role == models.UserRole.OWNER.value:
            raise HTTPException(status_code=400, detail="No se puede eliminar al dueño de la empresa.")
            
        # 4. Archivar (Soft Delete + Release Email)
        return await crud.archive_user(db, user)