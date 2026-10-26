from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


MongoId = Annotated[
    str,
    BeforeValidator(str),
    Field(pattern=r"^[0-9a-fA-F]{24}$"),
]


class ProductoPedidoCreate(BaseModel):
    producto_id: MongoId
    cantidad: int = Field(gt=0)


class ProductoPedido(ProductoPedidoCreate):
    nombre: str = Field(min_length=1, max_length=120)
    precio_unitario: float = Field(gt=0)


class PedidoCreate(BaseModel):
    usuario_id: MongoId
    productos: list[ProductoPedidoCreate] = Field(min_length=1)


class Pedido(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: MongoId | None = Field(default=None, alias="_id")
    usuario_id: MongoId
    productos: list[ProductoPedido] = Field(min_length=1)
    total: float = Field(gt=0)
    estado: Literal["pendiente", "pagado", "enviado", "entregado", "cancelado"] = (
        "pendiente"
    )
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))