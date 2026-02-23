from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructure.db import Base


class ClassSessionORM(Base):
    __tablename__ = "class_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    schedule: Mapped[str] = mapped_column(String(80), nullable=False)  # simple: "Lun 6pm"
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    trainer_id: Mapped[int] = mapped_column(Integer, nullable=False)