from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo import ReturnDocument

from model.auth import solo_admin
from model.database import db_manager
from model.productos import Producto, ProductoCreate

router = APIRouter(prefix="/productos", tags=["Productos"])


def validar_id(producto_id: str) -> ObjectId:
    if not ObjectId.is_valid(producto_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El ID del producto no es válido.",
        )
    return ObjectId(producto_id)


def serializar_producto(documento: dict) -> dict:
    return {
        "id": str(documento["_id"]),
        "nombre": documento["nombre"],
        "descripcion": documento["descripcion"],
        "precio": documento["precio"],
        "unidades": documento.get("unidades", documento.get("stock", 0)),
        "activo": documento.get("activo", True),
        "imagen": documento.get("imagen"),
    }


@router.get("/", response_model=list[Producto])
async def listar_productos():
    documentos = await db_manager.db.productos.find({}).to_list(length=None)
    return [serializar_producto(documento) for documento in documentos]


@router.get("/{producto_id}", response_model=Producto)
async def obtener_producto(producto_id: str):
    documento = await db_manager.db.productos.find_one(
        {"_id": validar_id(producto_id)}
    )
    if documento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )
    return serializar_producto(documento)


@router.post(
    "/",
    response_model=Producto,
    status_code=status.HTTP_201_CREATED,
)
async def crear_producto(
    producto: ProductoCreate,
    _admin: dict = Depends(solo_admin),
):
    datos = producto.model_dump()
    resultado = await db_manager.db.productos.insert_one(datos.copy())
    return {"id": str(resultado.inserted_id), **datos}


@router.put("/{producto_id}", response_model=Producto)
async def actualizar_producto(
    producto_id: str,
    producto: ProductoCreate,
    _admin: dict = Depends(solo_admin),
):
    documento = await db_manager.db.productos.find_one_and_update(
        {"_id": validar_id(producto_id)},
        {"$set": producto.model_dump()},
        return_document=ReturnDocument.AFTER,
    )
    if documento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )
    return serializar_producto(documento)


@router.delete("/{producto_id}")
async def eliminar_producto(
    producto_id: str,
    _admin: dict = Depends(solo_admin),
):
    resultado = await db_manager.db.productos.delete_one(
        {"_id": validar_id(producto_id)}
    )
    if resultado.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )
    return {"mensaje": "Producto eliminado."}
