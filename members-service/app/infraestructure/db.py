from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./members.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # requerido por SQLite en apps web
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    # Importa modelos para que SQLAlchemy los registre antes de create_all
    from app.infraestructure import models  # noqa: F401
   

    Base.metadata.create_all(bind=engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()