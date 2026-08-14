"""Supabase implementation of repository layer."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

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


class SupabasePatientRepository(PatientRepository):
    def create(self, patient: PatientModel) -> PatientModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = patient.model_dump(mode="json")
        res = self.client.table("patients").insert(data).execute()
        return PatientModel.model_validate(res.data[0])

    def get_by_id(self, patient_id: uuid.UUID) -> Optional[PatientModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("patients")
            .select("*")
            .eq("id", str(patient_id))
            .execute()
        )
        if not res.data:
            return None
        return PatientModel.model_validate(res.data[0])

    def get_by_email(self, email: str) -> Optional[PatientModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = self.client.table("patients").select("*").eq("email", email).execute()
        if not res.data:
            return None
        return PatientModel.model_validate(res.data[0])

    def get_by_external_id(self, external_user_id: str) -> Optional[PatientModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("patients")
            .select("*")
            .eq("external_user_id", external_user_id)
            .execute()
        )
        if not res.data:
            return None
        return PatientModel.model_validate(res.data[0])


class SupabaseDoctorRepository(DoctorRepository):
    def create(self, doctor: DoctorModel) -> DoctorModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = doctor.model_dump(mode="json")
        res = self.client.table("doctors").insert(data).execute()
        return DoctorModel.model_validate(res.data[0])

    def get_by_id(self, doctor_id: uuid.UUID) -> Optional[DoctorModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("doctors").select("*").eq("id", str(doctor_id)).execute()
        )
        if not res.data:
            return None
        return DoctorModel.model_validate(res.data[0])

    def list_active(self) -> List[DoctorModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = self.client.table("doctors").select("*").eq("is_active", True).execute()
        return [DoctorModel.model_validate(item) for item in res.data]

    def search_by_name(self, name_query: str) -> List[DoctorModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("doctors")
            .select("*")
            .ilike("name", f"%{name_query}%")
            .execute()
        )
        return [DoctorModel.model_validate(item) for item in res.data]

    def search(
        self,
        specialty: Optional[str] = None,
        doctor_name: Optional[str] = None,
        location: Optional[str] = None,
        clinic_name: Optional[str] = None,
        is_active: Optional[bool] = True,
        limit: int = 10,
    ) -> List[DoctorModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")

        query = self.client.table("doctors").select("*")
        if is_active is not None:
            query = query.eq("is_active", is_active)
        if doctor_name:
            query = query.ilike("name", f"%{doctor_name}%")
        if location:
            query = query.ilike("location", f"%{location}%")
        if clinic_name:
            query = query.ilike("clinic_name", f"%{clinic_name}%")

        query = query.limit(limit)
        res = query.execute()
        doctors = [DoctorModel.model_validate(item) for item in res.data]

        if specialty:
            filtered = []
            for doc in doctors:
                specs = self.get_specialties(doc.id)
                if any(specialty.lower() in s.name.lower() for s in specs):
                    filtered.append(doc)
            return filtered

        return doctors

    def add_specialty(self, doctor_id: uuid.UUID, specialty_id: uuid.UUID) -> None:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        self.client.table("doctor_specialties").insert(
            {"doctor_id": str(doctor_id), "specialty_id": str(specialty_id)}
        ).execute()

    def get_specialties(self, doctor_id: uuid.UUID) -> List[SpecialtyModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("doctor_specialties")
            .select("specialties(*)")
            .eq("doctor_id", str(doctor_id))
            .execute()
        )
        specialties = []
        for item in res.data:
            if "specialties" in item and item["specialties"]:
                specialties.append(SpecialtyModel.model_validate(item["specialties"]))
        return specialties


class SupabaseSpecialtyRepository(SpecialtyRepository):
    def create(self, specialty: SpecialtyModel) -> SpecialtyModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = specialty.model_dump(mode="json")
        res = self.client.table("specialties").insert(data).execute()
        return SpecialtyModel.model_validate(res.data[0])

    def get_by_id(self, specialty_id: uuid.UUID) -> Optional[SpecialtyModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("specialties")
            .select("*")
            .eq("id", str(specialty_id))
            .execute()
        )
        if not res.data:
            return None
        return SpecialtyModel.model_validate(res.data[0])

    def get_by_name(self, name: str) -> Optional[SpecialtyModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = self.client.table("specialties").select("*").eq("name", name).execute()
        if not res.data:
            return None
        return SpecialtyModel.model_validate(res.data[0])

    def list_all(self) -> List[SpecialtyModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = self.client.table("specialties").select("*").execute()
        return [SpecialtyModel.model_validate(item) for item in res.data]


class SupabaseAvailabilityRepository(AvailabilityRepository):
    def create(self, availability: DoctorAvailabilityModel) -> DoctorAvailabilityModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = availability.model_dump(mode="json")
        res = self.client.table("doctor_availability").insert(data).execute()
        return DoctorAvailabilityModel.model_validate(res.data[0])

    def get_by_id(
        self, availability_id: uuid.UUID
    ) -> Optional[DoctorAvailabilityModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("doctor_availability")
            .select("*")
            .eq("id", str(availability_id))
            .execute()
        )
        if not res.data:
            return None
        return DoctorAvailabilityModel.model_validate(res.data[0])

    def get_available_slots(
        self, doctor_id: uuid.UUID
    ) -> List[DoctorAvailabilityModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("doctor_availability")
            .select("*")
            .eq("doctor_id", str(doctor_id))
            .eq("status", "AVAILABLE")
            .execute()
        )
        return [DoctorAvailabilityModel.model_validate(item) for item in res.data]

    def get_by_doctor(self, doctor_id: uuid.UUID) -> List[DoctorAvailabilityModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("doctor_availability")
            .select("*")
            .eq("doctor_id", str(doctor_id))
            .execute()
        )
        return [DoctorAvailabilityModel.model_validate(item) for item in res.data]

    def search_available_slots(
        self,
        doctor_id: Optional[uuid.UUID] = None,
        start_after: Optional[datetime] = None,
        end_before: Optional[datetime] = None,
        limit: int = 20,
    ) -> List[DoctorAvailabilityModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")

        query = (
            self.client.table("doctor_availability")
            .select("*")
            .eq("status", "AVAILABLE")
        )
        if doctor_id:
            query = query.eq("doctor_id", str(doctor_id))
        if start_after:
            query = query.gte("start_time", start_after.isoformat())
        if end_before:
            query = query.lte("end_time", end_before.isoformat())

        query = query.order("start_time", desc=False).limit(limit)
        res = query.execute()
        return [DoctorAvailabilityModel.model_validate(item) for item in res.data]

    def update_status(
        self, availability_id: uuid.UUID, status: AvailabilityStatus
    ) -> Optional[DoctorAvailabilityModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("doctor_availability")
            .update({"status": status.value})
            .eq("id", str(availability_id))
            .execute()
        )
        if not res.data:
            return None
        return DoctorAvailabilityModel.model_validate(res.data[0])


class SupabaseAppointmentRepository(AppointmentRepository):
    def create(self, appointment: AppointmentModel) -> AppointmentModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = appointment.model_dump(mode="json")
        res = self.client.table("appointments").insert(data).execute()
        return AppointmentModel.model_validate(res.data[0])

    def get_by_id(self, appointment_id: uuid.UUID) -> Optional[AppointmentModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("appointments")
            .select("*")
            .eq("id", str(appointment_id))
            .execute()
        )
        if not res.data:
            return None
        return AppointmentModel.model_validate(res.data[0])

    def list_for_patient(self, patient_id: uuid.UUID) -> List[AppointmentModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("appointments")
            .select("*")
            .eq("patient_id", str(patient_id))
            .execute()
        )
        return [AppointmentModel.model_validate(item) for item in res.data]

    def list_for_doctor(self, doctor_id: uuid.UUID) -> List[AppointmentModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("appointments")
            .select("*")
            .eq("doctor_id", str(doctor_id))
            .execute()
        )
        return [AppointmentModel.model_validate(item) for item in res.data]

    def update_status(
        self, appointment_id: uuid.UUID, status: AppointmentStatus
    ) -> Optional[AppointmentModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("appointments")
            .update({"status": status.value})
            .eq("id", str(appointment_id))
            .execute()
        )
        if not res.data:
            return None
        return AppointmentModel.model_validate(res.data[0])

    def reschedule(
        self,
        appointment_id: uuid.UUID,
        new_start_time: datetime,
        new_end_time: datetime,
        status: AppointmentStatus = AppointmentStatus.CONFIRMED,
    ) -> Optional[AppointmentModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("appointments")
            .update(
                {
                    "start_time": new_start_time.isoformat(),
                    "end_time": new_end_time.isoformat(),
                    "status": status.value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", str(appointment_id))
            .execute()
        )
        if not res.data:
            return None
        return AppointmentModel.model_validate(res.data[0])


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
        updates = {
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


class SupabaseNotificationDeliveryRepository(NotificationDeliveryRepository):
    def create(self, delivery: NotificationDeliveryModel) -> NotificationDeliveryModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = delivery.model_dump(mode="json")
        res = self.client.table("notification_deliveries").insert(data).execute()
        return NotificationDeliveryModel.model_validate(res.data[0])

    def get_by_id(self, delivery_id: uuid.UUID) -> Optional[NotificationDeliveryModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("notification_deliveries")
            .select("*")
            .eq("id", str(delivery_id))
            .execute()
        )
        if not res.data:
            return None
        return NotificationDeliveryModel.model_validate(res.data[0])

    def update_status(
        self,
        delivery_id: uuid.UUID,
        status: NotificationStatus,
        provider_response_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[NotificationDeliveryModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        updates = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if provider_response_id is not None:
            updates["provider_response_id"] = provider_response_id
        if error_message is not None:
            updates["error_message"] = error_message

        res = (
            self.client.table("notification_deliveries")
            .update(updates)
            .eq("id", str(delivery_id))
            .execute()
        )
        if not res.data:
            return None
        return NotificationDeliveryModel.model_validate(res.data[0])
