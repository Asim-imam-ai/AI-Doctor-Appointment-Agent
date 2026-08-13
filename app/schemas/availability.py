"""Availability schemas."""

from datetime import datetime

from pydantic import BaseModel


class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    is_available: bool = True


class DoctorAvailabilityResponse(BaseModel):
    doctor_id: str
    available_slots: list[TimeSlot] = []
