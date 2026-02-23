from pydantic import BaseModel, Field


class EquipmentCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    quantity: int = Field(ge=0)  # regla: inventario no negativo


class EquipmentRead(EquipmentCreate):
    id: int