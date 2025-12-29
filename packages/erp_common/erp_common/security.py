from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os
from typing import Optional

# Configuración Criptográfica
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # 30 minutos
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --- UTILIDADES ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    """Crea un token de larga duración solo para renovar sesión."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Marcamos que este es un token de REFRESCO
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    """Decodifica el token sin verificar rol aun, útil para el refresh"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# --- PERMISOS ---
class Permissions:
    # FINANZAS
    INVOICE_READ = "invoice:read"
    INVOICE_CREATE = "invoice:create"
    INVOICE_VOID = "invoice:void"
    QUOTE_READ = "quote:read"
    QUOTE_CREATE = "quote:create"
    PAYMENT_CREATE = "payment:create"
    REPORTS_VIEW = "reports:view"
    
    # INVENTARIO
    PRODUCT_READ = "product:read"
    PRODUCT_CREATE = "product:create"
    PRODUCT_UPDATE = "product:update"
    PRODUCT_DELETE = "product:delete"
    STOCK_ADJUST = "stock:adjust"
    
    # CRM
    CUSTOMER_READ = "customer:read"
    CUSTOMER_CREATE = "customer:create"
    CUSTOMER_UPDATE = "customer:update"
    
    # RRHH
    EMPLOYEE_READ = "employee:read"
    EMPLOYEE_MANAGE = "employee:manage"
    NOTE_CREATE = "note:create"
    NOTE_READ_ALL = "note:read_all"
    PAYROLL_PROCESS = "payroll:process"
    SCHEDULE_MANAGE = "schedule:manage"
    
    # CONTABILIDAD
    ACCOUNTING_READ = "accounting:read"
    ACCOUNTING_MANAGE = "accounting:manage"
    
    # PROYECTOS
    PROJECT_READ = "project:read"
    PROJECT_CREATE = "project:create"
    PROJECT_UPDATE = "project:update"
    TASK_MANAGE = "task:manage"
    
    # SISTEMA
    USER_MANAGE = "user:manage" 

ROLE_PERMISSIONS = {
    "OWNER": ["*"], 
    "ADMIN": ["*"], 
    
    "SALES_AGENT": [
        Permissions.INVOICE_READ, 
        Permissions.INVOICE_CREATE, 
        Permissions.QUOTE_READ,
        Permissions.QUOTE_CREATE,
        Permissions.PAYMENT_CREATE,
        Permissions.PRODUCT_READ,
        Permissions.CUSTOMER_READ,
        Permissions.CUSTOMER_CREATE,
    ],
    "SALES_SUPERVISOR": [
        Permissions.INVOICE_READ, 
        Permissions.INVOICE_VOID,
        Permissions.QUOTE_READ,
        Permissions.REPORTS_VIEW,
        Permissions.PRODUCT_READ,
        Permissions.CUSTOMER_READ,
        Permissions.PROJECT_READ,
        Permissions.NOTE_CREATE
    ],
    
    "ACCOUNTANT": [
        Permissions.INVOICE_READ,
        Permissions.QUOTE_READ,
        Permissions.REPORTS_VIEW,
        Permissions.ACCOUNTING_READ,
        Permissions.ACCOUNTING_MANAGE,
        Permissions.PAYROLL_PROCESS
    ],

    "WAREHOUSE_CLERK": [
        Permissions.PRODUCT_READ,
        Permissions.PRODUCT_CREATE,
        Permissions.PRODUCT_UPDATE,
        Permissions.STOCK_ADJUST
    ],
    "WAREHOUSE_SUPERVISOR": [
        Permissions.PRODUCT_READ,
        Permissions.REPORTS_VIEW,
        Permissions.NOTE_CREATE,
        Permissions.PRODUCT_DELETE
    ],

    "RRHH_MANAGER": [
        Permissions.EMPLOYEE_READ,
        Permissions.EMPLOYEE_MANAGE,
        Permissions.PAYROLL_PROCESS,
        Permissions.SCHEDULE_MANAGE,
        Permissions.NOTE_CREATE,
        Permissions.NOTE_READ_ALL
    ],
    
    "PROJECT_MANAGER": [
        Permissions.PROJECT_READ, 
        Permissions.PROJECT_CREATE, 
        Permissions.PROJECT_UPDATE, 
        Permissions.TASK_MANAGE,
        Permissions.REPORTS_VIEW
    ]
}

# --- DEPENDENCIAS FASTAPI ---
class UserPayload:
    def __init__(self, sub: str, role: str, tenant_id: int, user_id: int):
        self.sub = sub
        self.role = role
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.permissions = ROLE_PERMISSIONS.get(role, [])

    def has_permission(self, required_perm: str) -> bool:
        if "*" in self.permissions: return True
        return required_perm in self.permissions

def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPayload:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o expiradas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        tenant_id: int = payload.get("tenant_id")
        user_id: int = payload.get("user_id")
        
        if email is None or tenant_id is None:
            raise credentials_exception
            
        return UserPayload(sub=email, role=role, tenant_id=tenant_id, user_id=user_id)
    except JWTError:
        raise credentials_exception

def get_current_tenant_id(user: UserPayload = Depends(get_current_user)) -> int:
    return user.tenant_id

class RequirePermission:
    def __init__(self, permission: str):
        self.permission = permission

    def __call__(self, user: UserPayload = Depends(get_current_user)):
        if not user.has_permission(self.permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Requieres permiso: {self.permission}"
            )
        return user