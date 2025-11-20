from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud, schemas, security, database, models

app = FastAPI(title="Auth Service", root_path="/api/auth")

# Crear tablas al iniciar (Solo para dev)
@app.on_event("startup")
async def startup():
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

@app.post("/register", response_model=schemas.UserResponse)
async def register(user: schemas.UserCreate, db: AsyncSession = Depends(database.get_db)):
    db_user = await crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Este Email ya está en uso")
    return await crud.create_user(db=db, user=user)

@app.post("/login", response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(database.get_db)):
    user = await crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}