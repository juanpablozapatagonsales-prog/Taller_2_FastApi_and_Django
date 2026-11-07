from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo import ReturnDocument

from model.auth import usuario_actual
from model.database import db_manager
from model.pedidos import Pedido, PedidoCreate, ProductoPedido

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def validar_id(id: str) -> ObjectId:
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="El ID no es válido")
    return ObjectId(id)


@router.post("/", response_model=Pedido, status_code=status.HTTP_201_CREATED)
async def crear_pedido(
    datos: PedidoCreate,
    usuario: dict = Depends(usuario_actual),
):
    cantidades = {}
    for item in datos.productos:
        cantidades[item.producto_id] = cantidades.get(item.producto_id, 0) + item.cantidad

    items = []
    total = 0
    productos_reservados = []
    for producto_id, cantidad in cantidades.items():
        object_id = validar_id(producto_id)
        producto = await db_manager.db.productos.find_one({"_id": object_id})
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {producto_id} no encontrado")
        if not producto.get("activo", True):
            raise HTTPException(status_code=400, detail=f"'{producto['nombre']}' no está disponible")

        unidades = producto.get("unidades", producto.get("stock", 0))
        if unidades < cantidad:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente de '{producto['nombre']}' (quedan {unidades})",
            )

        items.append(
            ProductoPedido(
                producto_id=producto_id,
                cantidad=cantidad,
                nombre=producto["nombre"],
                precio_unitario=producto["precio"],
            )
        )
        total += producto["precio"] * cantidad

    try:
        for item in items:
            object_id = ObjectId(item.producto_id)
            filtro_base = {
                "_id": object_id,
                "$or": [{"activo": True}, {"activo": {"$exists": False}}],
            }
            producto_antes = await db_manager.db.productos.find_one_and_update(
                {**filtro_base, "unidades": {"$gte": item.cantidad}},
                {"$inc": {"unidades": -item.cantidad}},
                return_document=ReturnDocument.BEFORE,
            )
            campo_stock = "unidades"
            if producto_antes is None:
                producto_antes = await db_manager.db.productos.find_one_and_update(
                    {
                        **filtro_base,
                        "unidades": {"$exists": False},
                        "stock": {"$gte": item.cantidad},
                    },
                    {"$inc": {"stock": -item.cantidad}},
                    return_document=ReturnDocument.BEFORE,
                )
                campo_stock = "stock"

            if producto_antes is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuficiente o producto no disponible: '{item.nombre}'.",
                )
            productos_reservados.append(
                (object_id, campo_stock, item.cantidad)
            )

        pedido = Pedido(
            usuario_id=usuario["id"],
            productos=items,
            total=round(total, 2),
        )
        documento_pedido = pedido.model_dump(exclude={"id"})
        resultado = await db_manager.db.pedidos.insert_one(documento_pedido)
    except Exception:
        for object_id, campo_stock, cantidad in reversed(productos_reservados):
            await db_manager.db.productos.update_one(
                {"_id": object_id},
                {"$inc": {campo_stock: cantidad}},
            )
        raise

    doc = {**documento_pedido, "_id": resultado.inserted_id}
    return doc


@router.get("/", response_model=list[Pedido])
async def listar_pedidos(usuario: dict = Depends(usuario_actual)):
    filtro = (
        {}
        if usuario["rol"] == "admin"
        else {"usuario_id": usuario["id"]}
    )
    return await db_manager.db.pedidos.find(filtro).to_list(length=100)


@router.get("/{pedido_id}", response_model=Pedido)
async def obtener_pedido(
    pedido_id: str,
    usuario: dict = Depends(usuario_actual),
):
    pedido = await db_manager.db.pedidos.find_one({"_id": validar_id(pedido_id)})
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if usuario["rol"] != "admin" and pedido["usuario_id"] != usuario["id"]:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver este pedido.")
    return pedido
