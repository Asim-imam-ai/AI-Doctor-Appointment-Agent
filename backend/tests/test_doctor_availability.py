"""Availability criteria, service delegation, and read-only graph boundary tests."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from app.agentic.common.tool_executor import AVAILABILITY_TOOLS
from app.agentic.workflows.availability.graph import build_doctor_availability_graph
from app.agentic.workflows.availability.nodes import classify_availability_intent_node
from app.agentic.workflows.availability.prompts import AVAILABILITY_SYSTEM_PROMPT
from app.agentic.workflows.availability.tools import execute_availability_search
from app.api.schemas.availability_agent import AvailabilitySearchCriteria
from app.domain.models import AvailabilityStatus, DoctorAvailabilityModel, DoctorModel


def test_availability_criteria_defaults_and_limits():
    criteria = AvailabilitySearchCriteria()
    assert criteria.user_timezone == "UTC"
    assert criteria.limit == 20


def test_availability_search_filters_past_slots():
    now = datetime.now(timezone.utc)
    doctor = DoctorModel(name="Dr. Ali")
    past = DoctorAvailabilityModel(
        doctor_id=doctor.id,
        start_time=now - timedelta(days=1),
        end_time=now - timedelta(days=1) + timedelta(minutes=30),
        status=AvailabilityStatus.AVAILABLE,
    )
    assert past.start_time < now
    future = DoctorAvailabilityModel(
        doctor_id=doctor.id,
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=1, minutes=30),
        status=AvailabilityStatus.AVAILABLE,
    )
    availability, doctors = Mock(), Mock()
    availability.search_slots.return_value = [future]
    doctors.get_doctor.return_value = doctor
    doctors.get_doctor_specialties.return_value = []

    result = execute_availability_search(
        AvailabilitySearchCriteria(doctor_id=doctor.id),
        availability_service=availability,
        doctor_service=doctors,
        current_time=now,
    )
    assert result.total == 1
    assert result.slots[0].id == future.id
    assert availability.search_slots.call_args.kwargs["start_after"] >= now


def test_availability_workflow_is_read_only_and_rejects_mutations():
    names = {tool.name for tool in AVAILABILITY_TOOLS}
    assert "search_available_slots" in names
    assert not any("booking" in name or "cancel" in name for name in names)
    assert (
        classify_availability_intent_node({"user_message": "book this slot for me"})[
            "intent"
        ]
        == "BOOKING_REQUEST"
    )
    assert (
        "cannot complete a booking"
        in classify_availability_intent_node({"user_message": "book this slot for me"})[
            "response"
        ].lower()
    )


def test_availability_agent_blocks_medical_advice():
    result = classify_availability_intent_node({"user_message": "diagnose my pain"})
    assert result["intent"] == "OUT_OF_SCOPE"


def test_availability_graph_and_prompt_are_present():
    assert build_doctor_availability_graph(llm=Mock()) is not None
    assert "cannot complete a booking" in AVAILABILITY_SYSTEM_PROMPT.lower()
