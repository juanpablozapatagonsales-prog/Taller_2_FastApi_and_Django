from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from pymongo import ReturnDocument

from model.database import db_manager
from model.productos import Producto, ProductoCreate, ProductoUpdate

router = APIRouter(prefix="/productos", tags=["Productos"])


def validar_id(id: str) -> ObjectId:
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="El ID no es válido")
    return ObjectId(id)


@router.post("/", response_model=Producto, status_code=status.HTTP_201_CREATED)
async def crear_producto(producto: ProductoCreate):
    doc = producto.model_dump()
    resultado = await db_manager.db.productos.insert_one(doc)
    doc["_id"] = resultado.inserted_id
    return doc


@router.get("/", response_model=list[Producto])
async def listar_productos(categoria: str | None = None, solo_activos: bool = True):
    filtro = {}
    if categoria:
        filtro["categoria"] = categoria
    if solo_activos:
        filtro["activo"] = True
    return await db_manager.db.productos.find(filtro).to_list(length=100)


@router.get("/{producto_id}", response_model=Producto)
async def obtener_producto(producto_id: str):
    producto = await db_manager.db.productos.find_one({"_id": validar_id(producto_id)})
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.put("/{producto_id}", response_model=Producto)
async def actualizar_producto(producto_id: str, datos: ProductoUpdate):
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(status_code=400, detail="No enviaste ningún dato para actualizar")

    producto = await db_manager.db.productos.find_one_and_update(
        {"_id": validar_id(producto_id)},
        {"$set": cambios},
        return_document=ReturnDocument.AFTER,
    )
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.delete("/{producto_id}")
async def eliminar_producto(producto_id: str):
    resultado = await db_manager.db.productos.delete_one({"_id": validar_id(producto_id)})
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"mensaje": "Producto eliminado"}
