import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI

from model.database import lifespan
from routers import pedidos, productos, usuarios

app = FastAPI(
    title="Taller FastAPI",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.include_router(usuarios.router)
app.include_router(productos.router)
app.include_router(pedidos.router)


@app.get("/", tags=["Inicio"])
async def inicio():
    return {"mensaje": "API funcionando"}
