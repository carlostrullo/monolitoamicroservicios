from pydantic import BaseModel, Field


class ClassCreate(BaseModel):
    name: str = Field(min_length=1)
    schedule: str = Field(min_length=1)
    max_capacity: int = Field(gt=0)
    trainer_id: int = Field(gt=0)


class ClassRead(ClassCreate):
    id: int