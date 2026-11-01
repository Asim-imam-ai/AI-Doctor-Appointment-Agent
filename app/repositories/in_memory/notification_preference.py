"""In-memory NotificationPreference repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from app.models import NotificationPreferenceModel
from app.repositories.base import NotificationPreferenceRepository


class InMemoryNotificationPreferenceRepository(NotificationPreferenceRepository):
    def __init__(self) -> None:
        super().__init__()
        self._storage: Dict[uuid.UUID, NotificationPreferenceModel] = {}

    def get_by_patient_id(
        self, patient_id: uuid.UUID
    ) -> Optional[NotificationPreferenceModel]:
        for pref in self._storage.values():
            if pref.patient_id == patient_id:
                return pref
        return None

    def create_or_update(
        self, preference: NotificationPreferenceModel
    ) -> NotificationPreferenceModel:
        existing = self.get_by_patient_id(preference.patient_id)
        if existing:
            updated = existing.model_copy(
                update={
                    "reminders_enabled": preference.reminders_enabled,
                    "email_enabled": preference.email_enabled,
                    "sms_enabled": preference.sms_enabled,
                    "in_app_enabled": preference.in_app_enabled,
                    "timezone": preference.timezone,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            self._storage[existing.id] = updated
            return updated
        self._storage[preference.id] = preference
        return preference
