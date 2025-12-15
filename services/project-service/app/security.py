from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "SECRET_SUPER_SECRETO_CAMBIAME")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ==============================================================================
# 🛡️ LISTA MAESTRA DE PERMISOS
# ==============================================================================
class Permissions:
    # FINANZAS (Facturación y Pagos)
    INVOICE_READ = "invoice:read"
    INVOICE_CREATE = "invoice:create"
    INVOICE_VOID = "invoice:void"
    QUOTE_READ = "quote:read"
    QUOTE_CREATE = "quote:create"
    PAYMENT_CREATE = "payment:create"
    REPORTS_VIEW = "reports:view"
    
    # INVENTARIO (Productos y Stock)
    PRODUCT_READ = "product:read"
    PRODUCT_CREATE = "product:create"
    PRODUCT_UPDATE = "product:update"
    STOCK_ADJUST = "stock:adjust"
    
    # CRM (Clientes)
    CUSTOMER_READ = "customer:read"
    CUSTOMER_CREATE = "customer:create"
    CUSTOMER_UPDATE = "customer:update"
    
    # RRHH (Empleados y Nómina)
    EMPLOYEE_READ = "employee:read"
    EMPLOYEE_MANAGE = "employee:manage"
    PAYROLL_PROCESS = "payroll:process"
    SCHEDULE_MANAGE = "schedule:manage"
    
    # CONTABILIDAD
    ACCOUNTING_READ = "accounting:read"   # Libros y Cuentas
    ACCOUNTING_MANAGE = "accounting:manage" # Asientos manuales, Importar PUC
    
    # PROYECTOS
    PROJECT_READ = "project:read"
    PROJECT_CREATE = "project:create"
    PROJECT_UPDATE = "project:update"
    TASK_MANAGE = "task:manage" # Crear/Mover tareas
    
    # SISTEMA
    USER_MANAGE = "user:manage" # Crear usuarios (Auth)

# ==============================================================================
# 👮 MATRIZ DE ROLES (RBAC)
# ==============================================================================
ROLE_PERMISSIONS = {
    "OWNER": ["*"], # Dios
    "ADMIN": ["*"], # Semidios
    
    # --- VENTAS ---
    "SALES_AGENT": [ # Cajero
        Permissions.INVOICE_READ, 
        Permissions.INVOICE_CREATE, 
        Permissions.QUOTE_READ,
        Permissions.QUOTE_CREATE,
        Permissions.PAYMENT_CREATE,
        Permissions.PRODUCT_READ,
        Permissions.CUSTOMER_READ,
        Permissions.CUSTOMER_CREATE, # Cajeros suelen registrar clientes nuevos
    ],
    "SALES_SUPERVISOR": [
        Permissions.INVOICE_READ, 
        Permissions.INVOICE_VOID, # Puede anular
        Permissions.QUOTE_READ,
        Permissions.REPORTS_VIEW,
        Permissions.PRODUCT_READ,
        Permissions.CUSTOMER_READ,
        Permissions.PROJECT_READ
    ],
    
    # --- CONTABILIDAD ---
    "ACCOUNTANT": [
        Permissions.INVOICE_READ,
        Permissions.QUOTE_READ,
        Permissions.REPORTS_VIEW,
        Permissions.ACCOUNTING_READ,
        Permissions.ACCOUNTING_MANAGE,
        Permissions.PROJECT_READ,
        Permissions.PAYROLL_PROCESS # A veces revisan nómina
    ],

    # --- INVENTARIO ---
    "WAREHOUSE_CLERK": [ # Almacenista
        Permissions.PRODUCT_READ,
        Permissions.PRODUCT_CREATE,
        Permissions.PRODUCT_UPDATE,
        Permissions.STOCK_ADJUST
    ],
    "WAREHOUSE_SUPERVISOR": [
        Permissions.PRODUCT_READ,
        Permissions.REPORTS_VIEW,
        Permissions.PROJECT_READ
    ],

    # --- RRHH ---
    "RRHH_MANAGER": [
        Permissions.EMPLOYEE_READ,
        Permissions.EMPLOYEE_MANAGE,
        Permissions.PAYROLL_PROCESS,
        Permissions.SCHEDULE_MANAGE
    ],
    
    # --- PROYECTOS ---
    "PROJECT_MANAGER": [
        Permissions.PROJECT_READ, 
        Permissions.PROJECT_CREATE, 
        Permissions.PROJECT_UPDATE, 
        Permissions.TASK_MANAGE
    ]
}

# ==============================================================================
# 🔐 LÓGICA DE VALIDACIÓN
# ==============================================================================

class UserPayload:
    def __init__(self, sub: str, role: str, tenant_id: int):
        self.sub = sub
        self.role = role
        self.tenant_id = tenant_id
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
        
        if email is None or tenant_id is None:
            raise credentials_exception
            
        return UserPayload(sub=email, role=role, tenant_id=tenant_id)
    except JWTError:
        raise credentials_exception

# Mantenemos esta para compatibilidad, pero ahora usa get_current_user internamente
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