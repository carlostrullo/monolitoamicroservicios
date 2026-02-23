from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructure.db import Base


class EquipmentORM(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)