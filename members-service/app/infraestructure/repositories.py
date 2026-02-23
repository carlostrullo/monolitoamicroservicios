from sqlalchemy.orm import Session
from sqlalchemy import select

from app.infraestructure.models import MemberORM
from app.domain.schemas import MemberCreate

from sqlalchemy import func, select
from app.infraestructure.models import MemberORM 


def create_member(db: Session, payload: MemberCreate) -> MemberORM:
    member = MemberORM(
        name=payload.name,
        email=str(payload.email),
        join_date=payload.join_date,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def list_members(db: Session) -> list[MemberORM]:
    return list(db.scalars(select(MemberORM)).all())




def get_member(db, member_id: int):
    return db.get(MemberORM, member_id)

def has_members(db) -> bool:
    total = db.scalar(select(func.count()).select_from(MemberORM))
    return (total or 0) > 0