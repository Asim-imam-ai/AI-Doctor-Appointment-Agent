"""Schemas and request/response models for Reminders and Notifications (Phase 7)."""

import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    ReminderModel,
)


class NotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: uuid.UUID
    reminders_enabled: bool
    email_enabled: bool
    sms_enabled: bool
    in_app_enabled: bool
    timezone: str


class UpdateNotificationPreferenceRequest(BaseModel):
    reminders_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    user_timezone: Optional[str] = Field(None, alias="timezone")


class ReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reminder: ReminderModel


class ListRemindersResponse(BaseModel):
    reminders: List[ReminderModel]
    total: int


class ProcessRemindersRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)


class ProcessRemindersResponse(BaseModel):
    processed_count: int
    results: List[dict]
