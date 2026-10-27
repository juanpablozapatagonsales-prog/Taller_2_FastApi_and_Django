from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext

from model.database import db_manager
from model.usuarios import UserCreate, UserResponse

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def registrar_usuario(user: UserCreate):
    existente = await db_manager.db.users.find_one({"email": user.email})
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo ya está registrado",
        )

    nuevo_usuario = {
        "email": user.email,
        "username": user.username,
        "hashed_password": pwd_context.hash(user.password),
    }
    resultado = await db_manager.db.users.insert_one(nuevo_usuario)

    return UserResponse(
        id=str(resultado.inserted_id),
        email=user.email,
        username=user.username,
    )
