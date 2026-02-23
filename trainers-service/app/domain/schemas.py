from pydantic import BaseModel, Field


class TrainerCreate(BaseModel):
    name: str = Field(min_length=1)
    specialty: str = Field(min_length=1)


class TrainerRead(TrainerCreate):
    id: int