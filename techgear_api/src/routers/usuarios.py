from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from pymongo.errors import DuplicateKeyError

from model.auth import create_access_token, usuario_actual
from model.database import db_manager
from model.usuarios import UserCreate, UserLogin, UserLoginResponse, UserResponse

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def serializar_usuario(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "correo": user.get("correo", user.get("email")),
        "rol": user.get("rol", "cliente"),
    }


@router.post(
    "/registro",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def registrar_usuario(user: UserCreate):
    correo = str(user.correo).strip().lower()
    existente = await db_manager.db.users.find_one({"correo": correo})
    if existente is None:
        existente = await db_manager.db.users.find_one({"email": correo})
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya está registrado",
        )

    nuevo_usuario = {
        "correo": correo,
        "username": user.username,
        "hashed_password": pwd_context.hash(user.password),
        "rol": "cliente",
    }
    try:
        resultado = await db_manager.db.users.insert_one(nuevo_usuario)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya está registrado",
        ) from error

    return {
        "id": str(resultado.inserted_id),
        "username": user.username,
        "correo": correo,
        "rol": "cliente",
    }


@router.post("/login", response_model=UserLoginResponse)
async def iniciar_sesion(user: UserLogin):
    correo = str(user.correo).strip().lower()
    existente = await db_manager.db.users.find_one({"correo": correo})
    if existente is None:
        existente = await db_manager.db.users.find_one({"email": correo})
    if not existente or not pwd_context.verify(
        user.password,
        existente["hashed_password"],
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El correo o la contraseña no son correctos",
        )

    if "rol" not in existente:
        existente["rol"] = "cliente"
    if "correo" not in existente:
        existente["correo"] = existente["email"]

    return {
        **serializar_usuario(existente),
        "access_token": create_access_token(existente),
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
async def obtener_usuario_actual(user: dict = Depends(usuario_actual)):
    return user
