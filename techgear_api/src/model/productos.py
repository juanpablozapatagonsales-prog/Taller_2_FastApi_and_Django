from pydantic import BaseModel, ConfigDict, Field


class ProductoBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str = Field(min_length=1, max_length=1000)
    precio: float = Field(ge=0)
    unidades: int = Field(ge=0)
    activo: bool = True
    imagen: str | None = None


class ProductoCreate(ProductoBase):
    pass


class Producto(ProductoBase):
    model_config = ConfigDict(extra="forbid")

    id: str
