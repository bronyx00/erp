from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "SECRET_SUPER_SECRETO_CAMBIAME")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Verifica si la contraseña plana coincide con el hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Genera el hash seguro de la contraseña."""
    return pwd_context.hash(password)

def create_access_token(data: dict):
    """
    Crea un JWT firmado.
    DATA debe incluir: 'sub' (email), 'tenand_id" y 'role'
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)