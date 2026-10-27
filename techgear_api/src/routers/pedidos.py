from bson import ObjectId
from fastapi import APIRouter, HTTPException, status

from model.database import db_manager
from model.pedidos import Pedido, PedidoCreate, ProductoPedido

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def validar_id(id: str) -> ObjectId:
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="El ID no es válido")
    return ObjectId(id)


@router.post("/", response_model=Pedido, status_code=status.HTTP_201_CREATED)
async def crear_pedido(datos: PedidoCreate):
    # 1. El usuario debe existir
    usuario = await db_manager.db.users.find_one({"_id": validar_id(datos.usuario_id)})
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # 2. Si un producto viene repetido, sumamos las cantidades
    cantidades = {}
    for item in datos.productos:
        cantidades[item.producto_id] = cantidades.get(item.producto_id, 0) + item.cantidad

    # 3. Validar cada producto y armar la lista del pedido
    items = []
    total = 0
    for producto_id, cantidad in cantidades.items():
        producto = await db_manager.db.productos.find_one({"_id": validar_id(producto_id)})
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {producto_id} no encontrado")
        if not producto["activo"]:
            raise HTTPException(status_code=400, detail=f"'{producto['nombre']}' no está disponible")
        if producto["stock"] < cantidad:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente de '{producto['nombre']}' (quedan {producto['stock']})",
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

    # 4. Descontar el stock
    for item in items:
        resultado = await db_manager.db.productos.update_one(
            {"_id": ObjectId(item.producto_id), "stock": {"$gte": item.cantidad}},
            {"$inc": {"stock": -item.cantidad}},
        )
        if resultado.modified_count == 0:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente de '{item.nombre}'")

    # 5. Guardar el pedido
    pedido = Pedido(usuario_id=datos.usuario_id, productos=items, total=round(total, 2))
    doc = pedido.model_dump(exclude={"id"})
    resultado = await db_manager.db.pedidos.insert_one(doc)
    doc["_id"] = resultado.inserted_id
    return doc


@router.get("/", response_model=list[Pedido])
async def listar_pedidos(usuario_id: str | None = None):
    filtro = {"usuario_id": usuario_id} if usuario_id else {}
    return await db_manager.db.pedidos.find(filtro).to_list(length=100)


@router.get("/{pedido_id}", response_model=Pedido)
async def obtener_pedido(pedido_id: str):
    pedido = await db_manager.db.pedidos.find_one({"_id": validar_id(pedido_id)})
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedido
