from sqlalchemy.orm import Session
from sqlalchemy import select

from app.infraestructure.models import EquipmentORM
from app.domain.schemas import EquipmentCreate

from sqlalchemy import func, select
from app.infraestructure.models import EquipmentORM  # ajusta si tu ORM se llama distinto


def create_equipment(db: Session, payload: EquipmentCreate) -> EquipmentORM:
    item = EquipmentORM(
        name=payload.name,
        description=payload.description,
        quantity=payload.quantity,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_equipment(db: Session) -> list[EquipmentORM]:
    return list(db.scalars(select(EquipmentORM)).all())


def get_equipment(db: Session, equipment_id: int) -> EquipmentORM | None:
    return db.get(EquipmentORM, equipment_id)


def has_equipment(db) -> bool:
    total = db.scalar(select(func.count()).select_from(EquipmentORM))
    return (total or 0) > 0