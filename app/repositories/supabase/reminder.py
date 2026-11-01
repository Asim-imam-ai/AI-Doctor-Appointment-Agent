"""Supabase Reminder repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.models import ReminderModel, ReminderStatus
from app.repositories.base import ReminderRepository


class SupabaseReminderRepository(ReminderRepository):
    def create(self, reminder: ReminderModel) -> ReminderModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = reminder.model_dump(mode="json")
        res = self.client.table("reminders").insert(data).execute()
        return ReminderModel.model_validate(res.data[0])

    def get_by_id(self, reminder_id: uuid.UUID) -> Optional[ReminderModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("reminders")
            .select("*")
            .eq("id", str(reminder_id))
            .execute()
        )
        if not res.data:
            return None
        return ReminderModel.model_validate(res.data[0])

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[ReminderModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("reminders")
            .select("*")
            .eq("idempotency_key", idempotency_key)
            .neq("status", "CANCELLED")
            .execute()
        )
        if not res.data:
            return None
        return ReminderModel.model_validate(res.data[0])

    def list_for_appointment(self, appointment_id: uuid.UUID) -> List[ReminderModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("reminders")
            .select("*")
            .eq("appointment_id", str(appointment_id))
            .execute()
        )
        return [ReminderModel.model_validate(item) for item in res.data]

    def list_for_patient(self, patient_id: uuid.UUID) -> List[ReminderModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("reminders")
            .select("*")
            .eq("patient_id", str(patient_id))
            .execute()
        )
        return [ReminderModel.model_validate(item) for item in res.data]

    def find_due_reminders(
        self, as_of_time: Optional[datetime] = None, limit: int = 50
    ) -> List[ReminderModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        check_time = as_of_time or datetime.now(timezone.utc)
        res = (
            self.client.table("reminders")
            .select("*")
            .eq("status", "PENDING")
            .lte("scheduled_at", check_time.isoformat())
            .order("scheduled_at", desc=False)
            .limit(limit)
            .execute()
        )
        return [ReminderModel.model_validate(item) for item in res.data]

    def claim_reminder(self, reminder_id: uuid.UUID) -> Optional[ReminderModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("reminders")
            .update(
                {
                    "status": "PROCESSING",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", str(reminder_id))
            .eq("status", "PENDING")
            .execute()
        )
        if not res.data:
            return None
        return ReminderModel.model_validate(res.data[0])

    def update_status(
        self,
        reminder_id: uuid.UUID,
        status: ReminderStatus,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
    ) -> Optional[ReminderModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        updates: dict = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if error_message is not None:
            updates["error_message"] = error_message
        if sent_at is not None:
            updates["sent_at"] = sent_at.isoformat()
        if cancelled_at is not None:
            updates["cancelled_at"] = cancelled_at.isoformat()
        res = (
            self.client.table("reminders")
            .update(updates)
            .eq("id", str(reminder_id))
            .execute()
        )
        if not res.data:
            return None
        return ReminderModel.model_validate(res.data[0])

    def cancel_for_appointment(self, appointment_id: uuid.UUID) -> int:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        now_utc = datetime.now(timezone.utc).isoformat()
        res = (
            self.client.table("reminders")
            .update(
                {
                    "status": "CANCELLED",
                    "cancelled_at": now_utc,
                    "updated_at": now_utc,
                }
            )
            .eq("appointment_id", str(appointment_id))
            .in_("status", ["PENDING", "PROCESSING"])
            .execute()
        )
        return len(res.data) if res.data else 0
