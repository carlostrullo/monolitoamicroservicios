from sqlalchemy.orm import Session
from sqlalchemy import select

from app.infraestructure.models import TrainerORM
from app.domain.schemas import TrainerCreate

from sqlalchemy import func, select
from app.infraestructure.models import TrainerORM  # ajusta el nombre si tu ORM se llama distinto


def create_trainer(db: Session, payload: TrainerCreate) -> TrainerORM:
    trainer = TrainerORM(name=payload.name, specialty=payload.specialty)
    db.add(trainer)
    db.commit()
    db.refresh(trainer)
    return trainer


def list_trainers(db: Session) -> list[TrainerORM]:
    return list(db.scalars(select(TrainerORM)).all())


def get_trainer(db: Session, trainer_id: int) -> TrainerORM | None:
    return db.get(TrainerORM, trainer_id)




def has_trainers(db) -> bool:
    total = db.scalar(select(func.count()).select_from(TrainerORM))
    return (total or 0) > 0