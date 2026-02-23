from datetime import date
from pydantic import BaseModel, EmailStr, Field


class MemberCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    join_date: date


class MemberRead(MemberCreate):
    id: int