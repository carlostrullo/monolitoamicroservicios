from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.infraestructure.models import ClassSessionORM
from app.domain.schemas import ClassCreate


def create_class(db: Session, payload: ClassCreate) -> ClassSessionORM:
    c = ClassSessionORM(
        name=payload.name,
        schedule=payload.schedule,
        max_capacity=payload.max_capacity,
        trainer_id=payload.trainer_id,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def list_classes(db: Session) -> list[ClassSessionORM]:
    return list(db.scalars(select(ClassSessionORM)).all())


def get_class(db: Session, class_id: int) -> ClassSessionORM | None:
    return db.get(ClassSessionORM, class_id)


def has_classes(db: Session) -> bool:
    total = db.scalar(select(func.count()).select_from(ClassSessionORM))
    return (total or 0) > 0