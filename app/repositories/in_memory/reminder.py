"""In-memory Reminder repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models import ReminderModel, ReminderStatus
from app.repositories.base import ReminderRepository


class InMemoryReminderRepository(ReminderRepository):
    def __init__(self) -> None:
        super().__init__()
        self._storage: Dict[uuid.UUID, ReminderModel] = {}

    def create(self, reminder: ReminderModel) -> ReminderModel:
        for r in self._storage.values():
            if (
                r.idempotency_key == reminder.idempotency_key
                and r.status != ReminderStatus.CANCELLED
            ):
                return r
        self._storage[reminder.id] = reminder
        return reminder

    def get_by_id(self, reminder_id: uuid.UUID) -> Optional[ReminderModel]:
        return self._storage.get(reminder_id)

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[ReminderModel]:
        for r in self._storage.values():
            if (
                r.idempotency_key == idempotency_key
                and r.status != ReminderStatus.CANCELLED
            ):
                return r
        return None

    def list_for_appointment(self, appointment_id: uuid.UUID) -> List[ReminderModel]:
        return [r for r in self._storage.values() if r.appointment_id == appointment_id]

    def list_for_patient(self, patient_id: uuid.UUID) -> List[ReminderModel]:
        return [r for r in self._storage.values() if r.patient_id == patient_id]

    def find_due_reminders(
        self, as_of_time: Optional[datetime] = None, limit: int = 50
    ) -> List[ReminderModel]:
        check_time = as_of_time or datetime.now(timezone.utc)
        check_compare = (
            check_time
            if check_time.tzinfo is not None
            else check_time.replace(tzinfo=timezone.utc)
        )
        due = []
        for r in self._storage.values():
            if r.status == ReminderStatus.PENDING:
                r_sched = (
                    r.scheduled_at
                    if r.scheduled_at.tzinfo is not None
                    else r.scheduled_at.replace(tzinfo=timezone.utc)
                )
                if r_sched <= check_compare:
                    due.append(r)
        due.sort(key=lambda x: x.scheduled_at)
        return due[:limit]

    def claim_reminder(self, reminder_id: uuid.UUID) -> Optional[ReminderModel]:
        r = self._storage.get(reminder_id)
        if not r or r.status != ReminderStatus.PENDING:
            return None
        updated = r.model_copy(
            update={
                "status": ReminderStatus.PROCESSING,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._storage[reminder_id] = updated
        return updated

    def update_status(
        self,
        reminder_id: uuid.UUID,
        status: ReminderStatus,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
    ) -> Optional[ReminderModel]:
        r = self._storage.get(reminder_id)
        if not r:
            return None
        updates: dict = {"status": status, "updated_at": datetime.now(timezone.utc)}
        if error_message is not None:
            updates["error_message"] = error_message
        if sent_at is not None:
            updates["sent_at"] = sent_at
        if cancelled_at is not None:
            updates["cancelled_at"] = cancelled_at
        updated = r.model_copy(update=updates)
        self._storage[reminder_id] = updated
        return updated

    def cancel_for_appointment(self, appointment_id: uuid.UUID) -> int:
        count = 0
        now_utc = datetime.now(timezone.utc)
        for r_id, r in list(self._storage.items()):
            if r.appointment_id == appointment_id and r.status in (
                ReminderStatus.PENDING,
                ReminderStatus.PROCESSING,
            ):
                updated = r.model_copy(
                    update={
                        "status": ReminderStatus.CANCELLED,
                        "cancelled_at": now_utc,
                        "updated_at": now_utc,
                    }
                )
                self._storage[r_id] = updated
                count += 1
        return count
