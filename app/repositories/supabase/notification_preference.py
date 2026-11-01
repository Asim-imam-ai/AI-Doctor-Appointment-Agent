"""Supabase NotificationPreference repository implementation."""

import uuid
from typing import Optional

from app.models import NotificationPreferenceModel
from app.repositories.base import NotificationPreferenceRepository


class SupabaseNotificationPreferenceRepository(NotificationPreferenceRepository):
    def get_by_patient_id(
        self, patient_id: uuid.UUID
    ) -> Optional[NotificationPreferenceModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("notification_preferences")
            .select("*")
            .eq("patient_id", str(patient_id))
            .execute()
        )
        if not res.data:
            return None
        return NotificationPreferenceModel.model_validate(res.data[0])

    def create_or_update(
        self, preference: NotificationPreferenceModel
    ) -> NotificationPreferenceModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = preference.model_dump(mode="json")
        res = (
            self.client.table("notification_preferences")
            .upsert(data, on_conflict="patient_id")
            .execute()
        )
        return NotificationPreferenceModel.model_validate(res.data[0])
