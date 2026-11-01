"""Patient schemas."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)


class PatientCreate(PatientBase):
    pass


class PatientResponse(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
