"""Reminder calculation, scheduling, revalidation, and worker execution service (Phase 7)."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.models import (
    AppointmentModel,
    AppointmentStatus,
    NotificationChannel,
    NotificationPreferenceModel,
    ReminderModel,
    ReminderStatus,
    ReminderType,
)
from app.repositories import (
    get_appointment_repository,
    get_doctor_repository,
    get_notification_preference_repository,
    get_patient_repository,
    get_reminder_repository,
)
from app.repositories.base import (
    AppointmentRepository,
    DoctorRepository,
    NotificationPreferenceRepository,
    PatientRepository,
    ReminderRepository,
)
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ReminderService:
    """Service owning deterministic reminder scheduling, preference resolution, revalidation, and processing."""

    def __init__(
        self,
        reminder_repo: Optional[ReminderRepository] = None,
        appointment_repo: Optional[AppointmentRepository] = None,
        patient_repo: Optional[PatientRepository] = None,
        doctor_repo: Optional[DoctorRepository] = None,
        preference_repo: Optional[NotificationPreferenceRepository] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        self.reminder_repo = reminder_repo or get_reminder_repository()
        self.appointment_repo = appointment_repo or get_appointment_repository()
        self.patient_repo = patient_repo or get_patient_repository()
        self.doctor_repo = doctor_repo or get_doctor_repository()
        self.preference_repo = (
            preference_repo or get_notification_preference_repository()
        )
        self.notification_service = notification_service or NotificationService()

    def get_user_preferences(
        self, patient_id: uuid.UUID
    ) -> NotificationPreferenceModel:
        """Retrieves or creates default notification preferences for patient."""
        pref = self.preference_repo.get_by_patient_id(patient_id)
        if not pref:
            pref = NotificationPreferenceModel(
                patient_id=patient_id,
                reminders_enabled=True,
                email_enabled=True,
                sms_enabled=False,
                in_app_enabled=True,
                timezone="UTC",
            )
            pref = self.preference_repo.create_or_update(pref)
        return pref

    def update_user_preferences(
        self,
        patient_id: uuid.UUID,
        reminders_enabled: Optional[bool] = None,
        email_enabled: Optional[bool] = None,
        sms_enabled: Optional[bool] = None,
        in_app_enabled: Optional[bool] = None,
        user_timezone: Optional[str] = None,
    ) -> NotificationPreferenceModel:
        """Updates notification preferences for authenticated patient."""
        current = self.get_user_preferences(patient_id)
        updated = current.model_copy(
            update={
                "reminders_enabled": (
                    reminders_enabled
                    if reminders_enabled is not None
                    else current.reminders_enabled
                ),
                "email_enabled": (
                    email_enabled
                    if email_enabled is not None
                    else current.email_enabled
                ),
                "sms_enabled": (
                    sms_enabled if sms_enabled is not None else current.sms_enabled
                ),
                "in_app_enabled": (
                    in_app_enabled
                    if in_app_enabled is not None
                    else current.in_app_enabled
                ),
                "timezone": (
                    user_timezone if user_timezone is not None else current.timezone
                ),
                "updated_at": datetime.now(timezone.utc),
            }
        )
        return self.preference_repo.create_or_update(updated)

    def calculate_reminder_times(
        self, appointment_start: datetime, user_tz: str = "UTC"
    ) -> List[tuple[ReminderType, datetime]]:
        """Calculates deterministic reminder times (24h and 2h before appointment)."""
        start_utc = (
            appointment_start
            if appointment_start.tzinfo is not None
            else appointment_start.replace(tzinfo=timezone.utc)
        )
        reminders = [
            (
                ReminderType.TWENTY_FOUR_HOURS_BEFORE,
                start_utc - timedelta(hours=24),
            ),
            (
                ReminderType.TWO_HOURS_BEFORE,
                start_utc - timedelta(hours=2),
            ),
        ]
        return reminders

    def schedule_reminders_for_appointment(
        self, appointment: AppointmentModel
    ) -> List[ReminderModel]:
        """Schedules 24h and 2h reminders for a newly created or rescheduled appointment."""
        if appointment.status in (
            AppointmentStatus.CANCELLED,
            AppointmentStatus.COMPLETED,
            AppointmentStatus.EXPIRED,
        ):
            return []

        patient = self.patient_repo.get_by_id(appointment.patient_id)
        user_tz = patient.timezone if patient else "UTC"

        scheduled_reminders = []
        now_utc = datetime.now(timezone.utc)

        for reminder_type, sched_time in self.calculate_reminder_times(
            appointment.start_time, user_tz
        ):
            # If scheduled time is in the past, skip creating stale schedule
            if sched_time <= now_utc:
                continue

            idem_key = (
                f"{appointment.id}:{reminder_type.value}:{sched_time.isoformat()}"
            )
            reminder = ReminderModel(
                appointment_id=appointment.id,
                patient_id=appointment.patient_id,
                reminder_type=reminder_type,
                scheduled_at=sched_time,
                status=ReminderStatus.PENDING,
                timezone=user_tz,
                idempotency_key=idem_key,
            )
            saved = self.reminder_repo.create(reminder)
            scheduled_reminders.append(saved)

        return scheduled_reminders

    def invalidate_reminders_for_appointment(self, appointment_id: uuid.UUID) -> int:
        """Cancels all pending reminders when an appointment is cancelled or rescheduled."""
        return self.reminder_repo.cancel_for_appointment(appointment_id)

    def revalidate_appointment_for_reminder(
        self, reminder: ReminderModel
    ) -> tuple[bool, Optional[str], Optional[AppointmentModel]]:
        """Revalidates appointment existence, ownership, and active status prior to sending reminder."""
        appt = self.appointment_repo.get_by_id(reminder.appointment_id)
        if not appt:
            return False, "Appointment not found.", None
        if appt.patient_id != reminder.patient_id:
            return False, "Patient identity mismatch.", appt
        if appt.status in (
            AppointmentStatus.CANCELLED,
            AppointmentStatus.COMPLETED,
            AppointmentStatus.EXPIRED,
        ):
            return (
                False,
                f"Appointment status is '{appt.status.value}' (not active).",
                appt,
            )

        now_utc = datetime.now(timezone.utc)
        appt_start_utc = (
            appt.start_time
            if appt.start_time.tzinfo is not None
            else appt.start_time.replace(tzinfo=timezone.utc)
        )
        if appt_start_utc <= now_utc:
            return False, "Appointment start time has already passed.", appt

        return True, None, appt

    def process_due_reminders(
        self, as_of_time: Optional[datetime] = None, limit: int = 50
    ) -> List[dict]:
        """Worker execution method to claim and process due reminders safely."""
        now_utc = as_of_time or datetime.now(timezone.utc)
        due_reminders = self.reminder_repo.find_due_reminders(
            as_of_time=now_utc, limit=limit
        )

        results = []
        for rem in due_reminders:
            # 1. Claim work atomically
            claimed = self.reminder_repo.claim_reminder(rem.id)
            if not claimed:
                continue  # Another worker claimed it

            # 2. Revalidate appointment status
            valid, reason, appt = self.revalidate_appointment_for_reminder(claimed)
            if not valid:
                self.reminder_repo.update_status(
                    reminder_id=claimed.id,
                    status=ReminderStatus.SKIPPED,
                    error_message=reason,
                    cancelled_at=now_utc,
                )
                results.append(
                    {
                        "reminder_id": str(claimed.id),
                        "status": "SKIPPED",
                        "reason": reason,
                    }
                )
                continue

            # 3. Check user preferences
            prefs = self.get_user_preferences(claimed.patient_id)
            if not prefs.reminders_enabled or not prefs.email_enabled:
                self.reminder_repo.update_status(
                    reminder_id=claimed.id,
                    status=ReminderStatus.SKIPPED,
                    error_message="User notification preferences disabled.",
                )
                results.append(
                    {
                        "reminder_id": str(claimed.id),
                        "status": "SKIPPED",
                        "reason": "User preferences disabled",
                    }
                )
                continue

            patient = self.patient_repo.get_by_id(claimed.patient_id)
            doctor = self.doctor_repo.get_by_id(appt.doctor_id) if appt else None
            doctor_name = doctor.name if doctor else "your doctor"
            recipient_email = patient.email if patient else "patient@example.com"

            # 4. Format template
            time_str = appt.start_time.strftime("%Y-%m-%d at %H:%M UTC")
            if claimed.reminder_type == ReminderType.TWENTY_FOUR_HOURS_BEFORE:
                subject = f"Reminder: Upcoming Appointment Tomorrow with {doctor_name}"
                body = (
                    f"Hello,\n\nThis is a reminder that you have an upcoming appointment "
                    f"with {doctor_name} tomorrow on {time_str}.\n\nThank you!"
                )
            else:
                subject = (
                    f"Reminder: Upcoming Appointment in 2 Hours with {doctor_name}"
                )
                body = (
                    f"Hello,\n\nThis is a reminder that your appointment with {doctor_name} "
                    f"is starting in approximately 2 hours on {time_str}.\n\nThank you!"
                )

            # 5. Send notification via provider
            delivery = self.notification_service.send_notification(
                reminder_id=claimed.id,
                patient_id=claimed.patient_id,
                recipient=recipient_email,
                subject=subject,
                body=body,
                channel=NotificationChannel.EMAIL,
            )

            if delivery.status == delivery.status.SENT:
                self.reminder_repo.update_status(
                    reminder_id=claimed.id,
                    status=ReminderStatus.SENT,
                    sent_at=now_utc,
                )
                results.append(
                    {
                        "reminder_id": str(claimed.id),
                        "status": "SENT",
                        "delivery_id": str(delivery.id),
                    }
                )
            else:
                # Failure handling with retry count tracking
                new_retry = claimed.retry_count + 1
                if new_retry >= claimed.max_retries:
                    self.reminder_repo.update_status(
                        reminder_id=claimed.id,
                        status=ReminderStatus.FAILED,
                        error_message=f"Permanent delivery failure: {delivery.error_message}",
                    )
                    results.append(
                        {
                            "reminder_id": str(claimed.id),
                            "status": "FAILED",
                            "error": delivery.error_message,
                        }
                    )
                else:
                    # Reset status to PENDING for transient retry and increment retry_count
                    self.reminder_repo.update_status(
                        reminder_id=claimed.id,
                        status=ReminderStatus.PENDING,
                        error_message=f"Transient failure (attempt {new_retry}): {delivery.error_message}",
                    )
                    # Manually update retry_count on repository model
                    rem_obj = self.reminder_repo.get_by_id(claimed.id)
                    if rem_obj:
                        rem_obj.retry_count = new_retry
                    results.append(
                        {
                            "reminder_id": str(claimed.id),
                            "status": "RETRYING",
                            "attempt": new_retry,
                        }
                    )

        return results
