"""Deterministic Read-Only Doctor Search Tool."""

import uuid
from typing import List, Optional

from langchain_core.tools import tool

from app.schemas.doctor_discovery import (
    DoctorDetail,
    DoctorSearchCriteria,
    DoctorSearchResult,
)
from app.services import DoctorService


def execute_doctor_search(
    criteria: DoctorSearchCriteria, doctor_service: Optional[DoctorService] = None
) -> DoctorSearchResult:
    service = doctor_service or DoctorService()
    bounded_limit = min(max(1, criteria.limit), 20)

    doctors = service.search_doctors(
        specialty=criteria.specialty,
        doctor_name=criteria.doctor_name,
        location=criteria.location,
        clinic_name=criteria.clinic_name,
        is_active=criteria.is_active,
        limit=bounded_limit,
    )

    doctor_details: List[DoctorDetail] = []
    for doc in doctors:
        specs = service.get_doctor_specialties(doc.id)
        spec_names = [s.name for s in specs]
        doctor_details.append(
            DoctorDetail(
                id=doc.id,
                name=doc.name,
                specialties=spec_names,
                clinic_name=doc.clinic_name,
                location=doc.location,
                bio=doc.bio,
                consultation_duration=doc.consultation_duration,
                is_active=doc.is_active,
            )
        )

    return DoctorSearchResult(
        doctors=doctor_details,
        total=len(doctor_details),
        criteria=criteria,
    )


@tool("search_doctors", args_schema=DoctorSearchCriteria)
def search_doctors_tool(
    specialty: Optional[str] = None,
    doctor_name: Optional[str] = None,
    location: Optional[str] = None,
    clinic_name: Optional[str] = None,
    is_active: bool = True,
    limit: int = 10,
) -> str:
    """Search active doctors using deterministic database criteria.

    Supports filtering by specialty, doctor_name, location, and clinic_name.
    Does NOT book, reschedule, or check real-time appointment slot availability.
    """
    criteria = DoctorSearchCriteria(
        specialty=specialty,
        doctor_name=doctor_name,
        location=location,
        clinic_name=clinic_name,
        is_active=is_active,
        limit=limit,
    )
    result = execute_doctor_search(criteria)
    return result.model_dump_json()


@tool("get_doctor_details")
def get_doctor_details_tool(doctor_id: str) -> str:
    """Retrieve detailed doctor profile information by doctor UUID."""
    service = DoctorService()
    try:
        doc_uuid = uuid.UUID(doctor_id)
    except ValueError:
        return '{"error": "Invalid UUID format for doctor_id"}'

    doc = service.get_doctor(doc_uuid)
    if not doc:
        return '{"error": "Doctor not found"}'

    specs = service.get_doctor_specialties(doc.id)
    detail = DoctorDetail(
        id=doc.id,
        name=doc.name,
        specialties=[s.name for s in specs],
        clinic_name=doc.clinic_name,
        location=doc.location,
        bio=doc.bio,
        consultation_duration=doc.consultation_duration,
        is_active=doc.is_active,
    )
    return detail.model_dump_json()
