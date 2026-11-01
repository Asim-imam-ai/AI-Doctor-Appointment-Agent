"""Deterministic Read-Only Availability Search Tool."""

import uuid
import zoneinfo
from datetime import datetime, time, timezone
from typing import List, Optional

from langchain_core.tools import tool

from app.api.schemas.availability_agent import (
    AvailabilitySearchCriteria,
    AvailabilitySearchResult,
    AvailableSlotDetail,
    TimeOfDay,
)
from app.domain import AvailabilityService, DoctorService


def execute_availability_search(
    criteria: AvailabilitySearchCriteria,
    availability_service: Optional[AvailabilityService] = None,
    doctor_service: Optional[DoctorService] = None,
    current_time: Optional[datetime] = None,
) -> AvailabilitySearchResult:
    if availability_service is None or doctor_service is None:
        from app.infrastructure.db.services import (
            get_availability_service,
            get_doctor_service,
        )

        availability_service = availability_service or get_availability_service()
        doctor_service = doctor_service or get_doctor_service()
    avail_service = availability_service
    doc_service = doctor_service

    now_utc = current_time or datetime.now(timezone.utc)

    # 1. Resolve matching doctors if doctor_name or specialty or location provided
    target_doctor_ids: Optional[List[uuid.UUID]] = None
    if criteria.doctor_id:
        target_doctor_ids = [criteria.doctor_id]
    elif criteria.doctor_name or criteria.specialty or criteria.location:
        matching_doctors = doc_service.search_doctors(
            specialty=criteria.specialty,
            doctor_name=criteria.doctor_name,
            location=criteria.location,
            limit=criteria.limit,
        )
        target_doctor_ids = [d.id for d in matching_doctors]
        if not target_doctor_ids:
            return AvailabilitySearchResult(slots=[], total=0, criteria=criteria)

    # 2. Date and Time-of-day resolution
    start_after_dt: Optional[datetime] = None
    end_before_dt: Optional[datetime] = None

    # Timezone resolution
    try:
        user_tz = zoneinfo.ZoneInfo(criteria.user_timezone)
    except Exception:
        user_tz = zoneinfo.ZoneInfo("UTC")

    if criteria.date:
        try:
            target_date = datetime.strptime(criteria.date, "%Y-%m-%d").date()
            if criteria.time_of_day == TimeOfDay.MORNING:
                t_start, t_end = time(8, 0), time(12, 0)
            elif criteria.time_of_day == TimeOfDay.AFTERNOON:
                t_start, t_end = time(12, 0), time(17, 0)
            elif criteria.time_of_day == TimeOfDay.EVENING:
                t_start, t_end = time(17, 0), time(21, 0)
            else:
                t_start, t_end = time(0, 0), time(23, 59, 59)

            dt_start_local = datetime.combine(target_date, t_start).replace(
                tzinfo=user_tz
            )
            dt_end_local = datetime.combine(target_date, t_end).replace(tzinfo=user_tz)

            start_after_dt = dt_start_local.astimezone(timezone.utc)
            end_before_dt = dt_end_local.astimezone(timezone.utc)
        except ValueError:
            pass

    if start_after_dt is None or start_after_dt < now_utc:
        start_after_dt = now_utc

    # 3. Retrieve available slots from service
    all_slots: List[AvailableSlotDetail] = []
    bounded_limit = min(max(1, criteria.limit), 50)

    if target_doctor_ids:
        for doc_id in target_doctor_ids:
            doc = doc_service.get_doctor(doc_id)
            if not doc or not doc.is_active:
                continue

            specs = doc_service.get_doctor_specialties(doc_id)
            spec_name = specs[0].name if specs else None

            raw_slots = avail_service.search_slots(
                doctor_id=doc_id,
                start_after=start_after_dt,
                end_before=end_before_dt,
                limit=bounded_limit,
            )

            for slot in raw_slots:
                all_slots.append(
                    AvailableSlotDetail(
                        id=slot.id,
                        doctor_id=slot.doctor_id,
                        doctor_name=doc.name,
                        specialty=spec_name,
                        clinic_name=doc.clinic_name,
                        location=doc.location,
                        start_time=slot.start_time,
                        end_time=slot.end_time,
                        timezone=criteria.user_timezone,
                        status=slot.status.value,
                    )
                )
    else:
        # Generic slot search without doctor filter
        raw_slots = avail_service.search_slots(
            doctor_id=None,
            start_after=start_after_dt,
            end_before=end_before_dt,
            limit=bounded_limit,
        )
        for slot in raw_slots:
            doc = doc_service.get_doctor(slot.doctor_id)
            if not doc or not doc.is_active:
                continue

            specs = doc_service.get_doctor_specialties(slot.doctor_id)
            spec_name = specs[0].name if specs else None

            all_slots.append(
                AvailableSlotDetail(
                    id=slot.id,
                    doctor_id=slot.doctor_id,
                    doctor_name=doc.name,
                    specialty=spec_name,
                    clinic_name=doc.clinic_name,
                    location=doc.location,
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    timezone=criteria.user_timezone,
                    status=slot.status.value,
                )
            )

    all_slots.sort(key=lambda s: s.start_time)
    final_slots = all_slots[:bounded_limit]

    return AvailabilitySearchResult(
        slots=final_slots, total=len(final_slots), criteria=criteria
    )


@tool("search_available_slots", args_schema=AvailabilitySearchCriteria)
def search_available_slots_tool(
    doctor_id: Optional[str] = None,
    doctor_name: Optional[str] = None,
    specialty: Optional[str] = None,
    location: Optional[str] = None,
    date: Optional[str] = None,
    time_of_day: Optional[str] = None,
    user_timezone: str = "UTC",
    limit: int = 20,
) -> str:
    """Search for real available doctor appointment slots using database records.

    Accepts doctor_name, specialty, location, date (YYYY-MM-DD), and time_of_day.
    Does NOT confirm, book, cancel, or reschedule appointments.
    """
    doc_uuid = None
    if doctor_id:
        try:
            doc_uuid = uuid.UUID(doctor_id)
        except ValueError:
            pass

    tod_enum = None
    if time_of_day:
        try:
            tod_enum = TimeOfDay(time_of_day.upper())
        except ValueError:
            pass

    criteria = AvailabilitySearchCriteria(
        doctor_id=doc_uuid,
        doctor_name=doctor_name,
        specialty=specialty,
        location=location,
        date=date,
        time_of_day=tod_enum,
        user_timezone=user_timezone,
        limit=limit,
    )
    result = execute_availability_search(criteria)
    return result.model_dump_json()
