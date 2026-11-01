"""Doctor schemas."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DoctorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    specialty: str = Field(..., min_length=1, max_length=100)
    bio: Optional[str] = None
    location: Optional[str] = None


class DoctorResponse(DoctorBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    available_days: List[str] = []
