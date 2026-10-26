from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from model.database import lifespan, db_manager

app = FastAPI(lifespan=lifespan)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserResponse(BaseModel):
    email: EmailStr
    username: str

@app.post("/usuarios/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def registrar_usuario(user: UserCreate):
    usuario_existente = await db_manager.db.users.find_one({"email": user.email})
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo ya está registrado"
        )

    hashed_password = pwd_context.hash(user.password)

    nuevo_usuario = {
        "email": user.email,
        "username": user.username,
        "hashed_password": hashed_password
    }

    await db_manager.db.users.insert_one(nuevo_usuario)

    return UserResponse(email=user.email, username=user.username)
