from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "SECRET_SUPER_SECRETO_CAMBIAME")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_tenant_id(token: str = Depends(oauth2_scheme)) -> int:
    """
    Valida el token y extrae el ID de la Empresa (Tenant ID).
    Esto permite que múltiples usuarios de la misma empresa vean los mismos datos.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        tenant_id: int = payload.get("tenant_id")
        if tenant_id is None:
            raise credentials_exception
        return tenant_id
    except JWTError:
        raise credentials_exception