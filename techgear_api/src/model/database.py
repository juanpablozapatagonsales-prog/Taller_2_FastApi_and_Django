import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import certifi

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

MONGO_URL = os.getenv("MONGO_URL", "").strip()
if MONGO_URL.startswith("MONGO_URL="):
    MONGO_URL = MONGO_URL.removeprefix("MONGO_URL=").strip()
MONGO_PASSWORD = os.getenv("CLAVE")
DATABASE_NAME = os.getenv("DATABASE_NAME", "Pedidos_y_productos")

if not MONGO_URL:
    raise RuntimeError("Falta MONGO_URL en el archivo .env")


def build_mongodb_url(url: str, password: str | None) -> str:
    parsed_url = urlsplit(url)
    if parsed_url.scheme not in {"mongodb", "mongodb+srv"} or not parsed_url.hostname:
        raise RuntimeError("MONGO_URL no contiene una URI válida de MongoDB")

    user_info, separator, host = parsed_url.netloc.rpartition("@")
    if not separator or not user_info:
        raise RuntimeError("MONGO_URL debe incluir el usuario de MongoDB")

    username, _, uri_password = user_info.partition(":")
    if not username:
        raise RuntimeError("MONGO_URL debe incluir el usuario de MongoDB")

    if not uri_password or (
        uri_password.startswith("<") and uri_password.endswith(">")
    ):
        if not password:
            raise RuntimeError("Configura la contraseña de MongoDB en la variable CLAVE")
        user_info = f"{username}:{quote(password, safe='')}"

    return urlunsplit(parsed_url._replace(netloc=f"{user_info}@{host}"))


MONGO_URL = build_mongodb_url(MONGO_URL, MONGO_PASSWORD)


class Database:
    client: AsyncIOMotorClient = None
    db = None


db_manager = Database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_manager.client = AsyncIOMotorClient(
        MONGO_URL,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000,
    )
    db_manager.db = db_manager.client[DATABASE_NAME]
    try:
        await db_manager.client.admin.command("ping")
        print("¡Conectado a MongoDB Atlas!")
    except Exception as e:
        print("Error de conexión:", e)
        raise
    yield
    db_manager.client.close()
    print("Conexión cerrada.")
