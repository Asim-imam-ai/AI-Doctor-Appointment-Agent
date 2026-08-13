"""Supabase implementation of repository layer."""

import uuid
from typing import List, Optional

from app.models import (
    AppointmentModel,
    AppointmentStatus,
    DoctorAvailabilityModel,
    DoctorModel,
    PatientModel,
    SpecialtyModel,
)
from app.repositories.base import (
    AppointmentRepository,
    AvailabilityRepository,
    DoctorRepository,
    PatientRepository,
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
