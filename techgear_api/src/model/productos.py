from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


MongoId = Annotated[
    str,
    BeforeValidator(str),
    Field(pattern=r"^[0-9a-fA-F]{24}$"),
]


class ProductoBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str = Field(min_length=1, max_length=1000)
    precio: float = Field(gt=0)
    stock: int = Field(ge=0)
    categoria: str = Field(min_length=1, max_length=80)
    imagen_url: str | None = None
    activo: bool = True


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    descripcion: str | None = Field(default=None, min_length=1, max_length=1000)
    precio: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    categoria: str | None = Field(default=None, min_length=1, max_length=80)
    imagen_url: str | None = None
    activo: bool | None = None


class Producto(ProductoBase):
    model_config = ConfigDict(populate_by_name=True)

    id: MongoId | None = Field(default=None, alias="_id")