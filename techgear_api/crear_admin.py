import asyncio
import sys
from pathlib import Path
from getpass import getpass

from fastapi import FastAPI
from passlib.context import CryptContext
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from model.database import db_manager, lifespan
from model.usuarios import UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def crear_admin(correo: str, username: str, password: str) -> None:
    user = UserCreate(
        correo=correo.strip().lower(),
        username=username,
        password=password,
    )
    async with lifespan(FastAPI()):
        existente = await db_manager.db.users.find_one({"correo": user.correo})
        if existente is None:
            existente = await db_manager.db.users.find_one({"email": user.correo})
        if existente:
            raise RuntimeError("Ya existe un usuario con ese correo.")

        try:
            await db_manager.db.users.insert_one(
                {
                    "correo": user.correo,
                    "username": user.username,
                    "hashed_password": pwd_context.hash(user.password),
                    "rol": "admin",
                }
            )
        except DuplicateKeyError as error:
            raise RuntimeError("Ya existe un usuario con ese correo.") from error


def main() -> None:
    username = input("Usuario: ").strip()
    correo = input("Correo electrónico: ").strip()
    password = getpass("Contraseña (mínimo 8 caracteres): ")

    try:
        asyncio.run(crear_admin(correo, username, password))
    except ValidationError as error:
        for detalle in error.errors():
            print(f"Error en {detalle['loc'][0]}: {detalle['msg']}")
        raise SystemExit(1) from error
    except RuntimeError as error:
        print(error)
        raise SystemExit(1) from error

    print("Administrador creado correctamente.")


if __name__ == "__main__":
    main()
