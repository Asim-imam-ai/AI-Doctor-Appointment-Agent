"""InMemory implementation of repository interfaces for testing and fallback."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models import (
    AppointmentModel,
    AppointmentStatus,
    AvailabilityStatus,
    DoctorAvailabilityModel,
    DoctorModel,
    NotificationDeliveryModel,
    NotificationPreferenceModel,
    NotificationStatus,
    PatientModel,
    ReminderModel,
    ReminderStatus,
    SpecialtyModel,
)
from app.repositories.base import (
    AppointmentRepository,
    AvailabilityRepository,
    DoctorRepository,
    NotificationDeliveryRepository,
    NotificationPreferenceRepository,
    PatientRepository,
    ReminderRepository,
    SpecialtyRepository,
)


class InMemoryPatientRepository(PatientRepository):
    def __init__(self):
        super().__init__()
        self._storage: Dict[uuid.UUID, PatientModel] = {}

    def create(self, patient: PatientModel) -> PatientModel:
        if any(p.email == patient.email for p in self._storage.values()):
            raise ValueError(f"Patient with email '{patient.email}' already exists.")
        if patient.external_user_id and any(
            p.external_user_id == patient.external_user_id
            for p in self._storage.values()
        ):
            raise ValueError(
                f"Patient with external_user_id "
                f"'{patient.external_user_id}' already exists."
            )

        self._storage[patient.id] = patient
        return patient

    def get_by_id(self, patient_id: uuid.UUID) -> Optional[PatientModel]:
        return self._storage.get(patient_id)

    def get_by_email(self, email: str) -> Optional[PatientModel]:
        for patient in self._storage.values():
            if patient.email.lower() == email.lower():
                return patient
        return None

    def get_by_external_id(self, external_user_id: str) -> Optional[PatientModel]:
        for patient in self._storage.values():
            if patient.external_user_id == external_user_id:
                return patient
        return None


class InMemoryDoctorRepository(DoctorRepository):
    def __init__(self):
        super().__init__()
        self._storage: Dict[uuid.UUID, DoctorModel] = {}
        self._doctor_specialties: Dict[uuid.UUID, List[uuid.UUID]] = {}
        self._specialty_repo: Optional[SpecialtyRepository] = None

    def set_specialty_repo(self, repo: SpecialtyRepository):
        self._specialty_repo = repo

    def create(self, doctor: DoctorModel) -> DoctorModel:
        self._storage[doctor.id] = doctor
        self._doctor_specialties[doctor.id] = []
        return doctor

    def get_by_id(self, doctor_id: uuid.UUID) -> Optional[DoctorModel]:
        return self._storage.get(doctor_id)

    def list_active(self) -> List[DoctorModel]:
        return [doc for doc in self._storage.values() if doc.is_active]

    def search_by_name(self, name_query: str) -> List[DoctorModel]:
        query = name_query.lower()
        return [doc for doc in self._storage.values() if query in doc.name.lower()]

    def search(
        self,
        specialty: Optional[str] = None,
        doctor_name: Optional[str] = None,
        location: Optional[str] = None,
        clinic_name: Optional[str] = None,
        is_active: Optional[bool] = True,
        limit: int = 10,
    ) -> List[DoctorModel]:
        results = []
        for doc in self._storage.values():
            if is_active is not None and doc.is_active != is_active:
                continue
            if doctor_name and doctor_name.lower() not in doc.name.lower():
                continue
            if location and (
                not doc.location or location.lower() not in doc.location.lower()
            ):
                continue
            if clinic_name and (
                not doc.clinic_name
                or clinic_name.lower() not in doc.clinic_name.lower()
            ):
                continue
            if specialty:
                doc_specs = self.get_specialties(doc.id)
                if not any(
                    specialty.lower() in spec.name.lower() for spec in doc_specs
                ):
                    continue
            results.append(doc)
            if len(results) >= limit:
                break
        return results

    def add_specialty(self, doctor_id: uuid.UUID, specialty_id: uuid.UUID) -> None:
        if doctor_id not in self._storage:
            raise ValueError(f"Doctor with ID '{doctor_id}' does not exist.")
        if doctor_id not in self._doctor_specialties:
            self._doctor_specialties[doctor_id] = []
        if specialty_id not in self._doctor_specialties[doctor_id]:
            self._doctor_specialties[doctor_id].append(specialty_id)

    def get_specialties(self, doctor_id: uuid.UUID) -> List[SpecialtyModel]:
        if doctor_id not in self._storage or not self._specialty_repo:
            return []
        specialty_ids = self._doctor_specialties.get(doctor_id, [])
        result = []
        for sid in specialty_ids:
            spec = self._specialty_repo.get_by_id(sid)
            if spec:
                result.append(spec)
        return result


class InMemorySpecialtyRepository(SpecialtyRepository):
    def __init__(self):
        super().__init__()
        self._storage: Dict[uuid.UUID, SpecialtyModel] = {}

    def create(self, specialty: SpecialtyModel) -> SpecialtyModel:
        if any(
            s.name.lower() == specialty.name.lower() for s in self._storage.values()
        ):
            raise ValueError(f"Specialty '{specialty.name}' already exists.")
        self._storage[specialty.id] = specialty
        return specialty

    def get_by_id(self, specialty_id: uuid.UUID) -> Optional[SpecialtyModel]:
        return self._storage.get(specialty_id)

    def get_by_name(self, name: str) -> Optional[SpecialtyModel]:
        for spec in self._storage.values():
            if spec.name.lower() == name.lower():
                return spec
        return None

    def list_all(self) -> List[SpecialtyModel]:
        return list(self._storage.values())


class InMemoryAvailabilityRepository(AvailabilityRepository):
    def __init__(self, doctor_repo: Optional[DoctorRepository] = None):
        super().__init__()
        self._storage: Dict[uuid.UUID, DoctorAvailabilityModel] = {}
        self.doctor_repo = doctor_repo

    def create(self, availability: DoctorAvailabilityModel) -> DoctorAvailabilityModel:
        if self.doctor_repo and not self.doctor_repo.get_by_id(availability.doctor_id):
            raise ValueError(f"Doctor ID '{availability.doctor_id}' does not exist.")
        self._storage[availability.id] = availability
        return availability

    def get_by_id(
        self, availability_id: uuid.UUID
    ) -> Optional[DoctorAvailabilityModel]:
        return self._storage.get(availability_id)

    def get_available_slots(
        self, doctor_id: uuid.UUID
    ) -> List[DoctorAvailabilityModel]:
        return [
            slot
            for slot in self._storage.values()
            if slot.doctor_id == doctor_id
            and slot.status == AvailabilityStatus.AVAILABLE
        ]

    def get_by_doctor(self, doctor_id: uuid.UUID) -> List[DoctorAvailabilityModel]:
        return [slot for slot in self._storage.values() if slot.doctor_id == doctor_id]

    def search_available_slots(
        self,
        doctor_id: Optional[uuid.UUID] = None,
        start_after: Optional[datetime] = None,
        end_before: Optional[datetime] = None,
        limit: int = 20,
    ) -> List[DoctorAvailabilityModel]:
        matching = []
        for slot in self._storage.values():
            if slot.status != AvailabilityStatus.AVAILABLE:
                continue
            if doctor_id and slot.doctor_id != doctor_id:
                continue
            if start_after and slot.start_time < start_after:
                continue
            if end_before and slot.end_time > end_before:
                continue
            matching.append(slot)

        matching.sort(key=lambda s: s.start_time)
        return matching[:limit]

    def update_status(
        self, availability_id: uuid.UUID, status: AvailabilityStatus
    ) -> Optional[DoctorAvailabilityModel]:
        slot = self._storage.get(availability_id)
        if not slot:
            return None
        updated_slot = slot.model_copy(
            update={"status": status, "updated_at": datetime.now(timezone.utc)}
        )
        self._storage[availability_id] = updated_slot
        return updated_slot


class InMemoryAppointmentRepository(AppointmentRepository):
    def __init__(
        self,
        patient_repo: Optional[PatientRepository] = None,
        doctor_repo: Optional[DoctorRepository] = None,
    ):
        super().__init__()
        self._storage: Dict[uuid.UUID, AppointmentModel] = {}
        self.patient_repo = patient_repo
        self.doctor_repo = doctor_repo

    def create(self, appointment: AppointmentModel) -> AppointmentModel:
        if self.patient_repo and not self.patient_repo.get_by_id(
            appointment.patient_id
        ):
            raise ValueError(f"Patient ID '{appointment.patient_id}' does not exist.")
        if self.doctor_repo:
            doctor = self.doctor_repo.get_by_id(appointment.doctor_id)
            if not doctor:
                raise ValueError(f"Doctor ID '{appointment.doctor_id}' does not exist.")
            if not doctor.is_active:
                raise ValueError(f"Doctor '{doctor.name}' is not active.")

        # Double-booking check for same doctor with overlapping non-cancelled
        # or non-expired appointments
        for appt in self._storage.values():
            if appt.doctor_id == appointment.doctor_id and appt.status in (
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED,
            ):
                # Overlap condition: start1 < end2 AND start2 < end1
                if (
                    appointment.start_time < appt.end_time
                    and appt.start_time < appointment.end_time
                ):
                    raise ValueError(
                        "Appointment time conflict for doctor "
                        f"'{appointment.doctor_id}'"
                    )

        self._storage[appointment.id] = appointment
        return appointment

    def get_by_id(self, appointment_id: uuid.UUID) -> Optional[AppointmentModel]:
        return self._storage.get(appointment_id)

    def list_for_patient(self, patient_id: uuid.UUID) -> List[AppointmentModel]:
        return [
            appt for appt in self._storage.values() if appt.patient_id == patient_id
        ]

    def list_for_doctor(self, doctor_id: uuid.UUID) -> List[AppointmentModel]:
        return [appt for appt in self._storage.values() if appt.doctor_id == doctor_id]

    def update_status(
        self, appointment_id: uuid.UUID, status: AppointmentStatus
    ) -> Optional[AppointmentModel]:
        appt = self._storage.get(appointment_id)
        if not appt:
            return None
        updated_appt = appt.model_copy(
            update={"status": status, "updated_at": datetime.now(timezone.utc)}
        )
        self._storage[appointment_id] = updated_appt
        return updated_appt

    def reschedule(
        self,
        appointment_id: uuid.UUID,
        new_start_time: datetime,
        new_end_time: datetime,
        status: AppointmentStatus = AppointmentStatus.CONFIRMED,
    ) -> Optional[AppointmentModel]:
        appt = self._storage.get(appointment_id)
        if not appt:
            return None
        updated_appt = appt.model_copy(
            update={
                "start_time": new_start_time,
                "end_time": new_end_time,
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._storage[appointment_id] = updated_appt
        return updated_appt


class InMemoryReminderRepository(ReminderRepository):
    def __init__(self):
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
        updates = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
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


class InMemoryNotificationPreferenceRepository(NotificationPreferenceRepository):
    def __init__(self):
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
        else:
            self._storage[preference.id] = preference
            return preference


class InMemoryNotificationDeliveryRepository(NotificationDeliveryRepository):
    def __init__(self):
        super().__init__()
        self._storage: Dict[uuid.UUID, NotificationDeliveryModel] = {}

    def create(self, delivery: NotificationDeliveryModel) -> NotificationDeliveryModel:
        self._storage[delivery.id] = delivery
        return delivery

    def get_by_id(self, delivery_id: uuid.UUID) -> Optional[NotificationDeliveryModel]:
        return self._storage.get(delivery_id)

    def update_status(
        self,
        delivery_id: uuid.UUID,
        status: NotificationStatus,
        provider_response_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[NotificationDeliveryModel]:
        d = self._storage.get(delivery_id)
        if not d:
            return None
        updates = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if provider_response_id is not None:
            updates["provider_response_id"] = provider_response_id
        if error_message is not None:
            updates["error_message"] = error_message

        updated = d.model_copy(update=updates)
        self._storage[delivery_id] = updated
        return updated
