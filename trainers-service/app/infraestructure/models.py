from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructure.db import Base


class TrainerORM(Base):
    __tablename__ = "trainers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    specialty: Mapped[str] = mapped_column(String(120), nullable=False)