import os
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

MONGODB_URL = os.getenv("MONGO_URL") or os.getenv("MONGO_URI")
MONGODB_PASSWORD = os.getenv("CLAVE")
DATABASE_NAME = os.getenv("DATABASE_NAME", "Cluster_FastAPI")

if not MONGODB_URL:
    raise RuntimeError("Falta configurar MONGO_URL en el archivo .env")
if not DATABASE_NAME:
    raise RuntimeError("Falta configurar DATABASE_NAME en el archivo .env")

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

    if password:
        user_info = f"{username}:{quote(password, safe='')}"
    elif not uri_password or uri_password.startswith("<") and uri_password.endswith(">"):
        raise RuntimeError("Configura la contraseña real de MongoDB en CLAVE")

    return urlunsplit(parsed_url._replace(netloc=f"{user_info}@{host}"))

MONGODB_URL = build_mongodb_url(MONGODB_URL, MONGODB_PASSWORD)

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_manager = Database()

async def lifespan(app: FastAPI):
    db_manager.client = AsyncIOMotorClient(MONGODB_URL)
    db_manager.db = db_manager.client[DATABASE_NAME]
    try:
        await db_manager.client.admin.command('ping')
        print("¡Conectado exitosamente a MongoDB Atlas!")
    except Exception as e:
        db_manager.client.close()
        raise RuntimeError("No se pudo conectar a MongoDB; verifica MONGO_URL") from e

    yield

    db_manager.client.close()
    print("Conexión cerrada.")
