from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import os
import logging

# Configuración (Debe coincidir con auth-service)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "SECRET_SUPER_SECRETO_CAMBIAME")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

logger = logging.getLogger("finance-security")

def get_current_user_email(token: str = Depends(oauth2_scheme)) -> str:
    """
    Valida el token JWT y extrae el email del usuario.
    Si el token es falso o expiró, lanza error 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se puede validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
    except JWTError as e:
        logger.warning(f"Intento de acceso con token inválido: {e}")
        raise credentials_exception