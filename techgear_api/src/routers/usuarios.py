from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from model.database import db_manager
from model.auth import create_access_token, get_token_user_id
from model.usuarios import UserAuthResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/", response_model=UserAuthResponse, status_code=status.HTTP_201_CREATED)
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

    return UserAuthResponse(
        id=str(resultado.inserted_id),
        email=user.email,
        username=user.username,
        access_token=create_access_token(str(resultado.inserted_id)),
    )


@router.post("/login", response_model=UserAuthResponse)
async def iniciar_sesion(user: UserLogin):
    existente = await db_manager.db.users.find_one({"email": user.email})
    if not existente or not pwd_context.verify(user.password, existente["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El correo o la contraseña no son correctos",
        )

    user_id = str(existente["_id"])
    return UserAuthResponse(
        id=user_id,
        email=existente["email"],
        username=existente["username"],
        access_token=create_access_token(user_id),
    )


@router.get("/me", response_model=UserResponse)
async def obtener_usuario_actual(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = get_token_user_id(credentials.credentials)
    if user_id is None or not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    existente = await db_manager.db.users.find_one({"_id": ObjectId(user_id)})
    if not existente:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario ya no existe",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserResponse(
        id=user_id,
        email=existente["email"],
        username=existente["username"],
    )
