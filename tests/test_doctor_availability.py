"""Unit, graph, API, and tool safety tests for Phase 4 Doctor Availability Agent."""

from datetime import datetime, timedelta, timezone
from typing import Any, List

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.agents import DoctorAvailabilityState, build_doctor_availability_graph
from app.agents.doctor_availability import classify_availability_intent_node
from app.core.prompts import AVAILABILITY_SYSTEM_PROMPT
from app.main import app
from app.models import AvailabilityStatus, DoctorAvailabilityModel
from app.repositories import (
    get_availability_repository,
    get_doctor_repository,
    get_specialty_repository,
)
from app.schemas.availability_agent import (
    AvailabilitySearchCriteria,
    AvailabilitySearchResult,
    TimeOfDay,
)
from app.services import AvailabilityService, DoctorService
from app.tools import AVAILABILITY_TOOLS
from app.tools.availability_search import (
    execute_availability_search,
    search_available_slots_tool,
)


@pytest.fixture
def seeded_availability_services():
    doc_repo = get_doctor_repository()
    spec_repo = get_specialty_repository()
    avail_repo = get_availability_repository()

    if hasattr(doc_repo, "_storage"):
        doc_repo._storage.clear()
    if hasattr(doc_repo, "_doctor_specialties"):
        doc_repo._doctor_specialties.clear()
    if hasattr(spec_repo, "_storage"):
        spec_repo._storage.clear()
    if hasattr(avail_repo, "_storage"):
        avail_repo._storage.clear()

    doc_service = DoctorService(doctor_repo=doc_repo, specialty_repo=spec_repo)
    avail_service = AvailabilityService(
        availability_repo=avail_repo, doctor_repo=doc_repo
    )

    d1 = doc_service.register_doctor(
        name="Dr. Ahmed Khan",
        bio="Cardiologist",
        clinic_name="Heart Care",
        location="Lahore",
    )
    doc_service.add_specialty_to_doctor(d1.id, "Cardiology")

    d2 = doc_service.register_doctor(
        name="Dr. Sarah Ali",
        bio="Dermatologist",
        clinic_name="Skin Care",
        location="Karachi",
    )
    doc_service.add_specialty_to_doctor(d2.id, "Dermatology")

    now = datetime.now(timezone.utc)
    t_tomorrow = (now + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )

    s1 = DoctorAvailabilityModel(
        doctor_id=d1.id,
        start_time=t_tomorrow,
        end_time=t_tomorrow + timedelta(minutes=30),
        status=AvailabilityStatus.AVAILABLE,
    )
    s2 = DoctorAvailabilityModel(
        doctor_id=d1.id,
        start_time=t_tomorrow + timedelta(hours=1),
        end_time=t_tomorrow + timedelta(hours=1, minutes=30),
        status=AvailabilityStatus.AVAILABLE,
    )
    s3 = DoctorAvailabilityModel(
        doctor_id=d2.id,
        start_time=t_tomorrow + timedelta(hours=2),
        end_time=t_tomorrow + timedelta(hours=2, minutes=30),
        status=AvailabilityStatus.AVAILABLE,
    )

    avail_repo.create(s1)
    avail_repo.create(s2)
    avail_repo.create(s3)

    return doc_service, avail_service, d1, d2, t_tomorrow


# ---------------------------------------------------------------------------
# 1. Criteria & Model Unit Tests
# ---------------------------------------------------------------------------


def test_availability_search_criteria_defaults():
    criteria = AvailabilitySearchCriteria()
    assert criteria.doctor_name is None
    assert criteria.specialty is None
    assert criteria.user_timezone == "UTC"
    assert criteria.limit == 20


def test_availability_search_criteria_validation():
    criteria = AvailabilitySearchCriteria(
        doctor_name="Ahmed", date="2026-08-20", time_of_day=TimeOfDay.MORNING
    )
    assert criteria.doctor_name == "Ahmed"
    assert criteria.time_of_day == TimeOfDay.MORNING


# ---------------------------------------------------------------------------
# 2. Deterministic Search Execution Tests
# ---------------------------------------------------------------------------


def test_execute_availability_search_by_doctor_name(seeded_availability_services):
    doc_service, avail_service, d1, d2, t_tomorrow = seeded_availability_services

    criteria = AvailabilitySearchCriteria(doctor_name="Ahmed")
    res = execute_availability_search(
        criteria,
        availability_service=avail_service,
        doctor_service=doc_service,
        current_time=t_tomorrow - timedelta(hours=1),
    )

    assert isinstance(res, AvailabilitySearchResult)
    assert res.total == 2
    assert res.slots[0].doctor_name == "Dr. Ahmed Khan"


def test_execute_availability_search_by_specialty(seeded_availability_services):
    doc_service, avail_service, d1, d2, t_tomorrow = seeded_availability_services

    criteria = AvailabilitySearchCriteria(specialty="Dermatology")
    res = execute_availability_search(
        criteria,
        availability_service=avail_service,
        doctor_service=doc_service,
        current_time=t_tomorrow - timedelta(hours=1),
    )

    assert res.total == 1
    assert res.slots[0].doctor_name == "Dr. Sarah Ali"


def test_execute_availability_search_past_slots_excluded(
    seeded_availability_services,
):
    doc_service, avail_service, d1, d2, t_tomorrow = seeded_availability_services

    criteria = AvailabilitySearchCriteria(doctor_name="Ahmed")
    # Current time is AFTER slots
    res = execute_availability_search(
        criteria,
        availability_service=avail_service,
        doctor_service=doc_service,
        current_time=t_tomorrow + timedelta(days=2),
    )

    assert res.total == 0


# ---------------------------------------------------------------------------
# 3. Tool & Allowlist Tests
# ---------------------------------------------------------------------------


def test_search_available_slots_tool_invocation(seeded_availability_services):
    output = search_available_slots_tool.invoke({"doctor_name": "Ahmed"})
    assert isinstance(output, str)
    assert "Dr. Ahmed Khan" in output


def test_availability_tools_allowlist():
    tool_names = [tool.name for tool in AVAILABILITY_TOOLS]
    assert "search_available_slots" in tool_names
    assert "search_doctors" in tool_names
    assert "get_doctor_details" in tool_names

    prohibited = [
        "book_appointment",
        "confirm_appointment",
        "cancel_appointment",
        "reschedule",
        "execute_sql",
    ]
    for name in tool_names:
        assert name not in prohibited


# ---------------------------------------------------------------------------
# 4. Intent Classification Safety Tests
# ---------------------------------------------------------------------------


def test_availability_intent_classification_valid():
    state: DoctorAvailabilityState = {
        "user_message": "Is Dr. Ahmed available tomorrow?",
        "user_timezone": "UTC",
        "messages": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "metadata": {},
    }
    res = classify_availability_intent_node(state)
    assert res["intent"] == "AVAILABILITY_SEARCH"


def test_availability_intent_classification_booking_rejected():
    state: DoctorAvailabilityState = {
        "user_message": "Book Dr. Ahmed at 10am tomorrow",
        "user_timezone": "UTC",
        "messages": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "metadata": {},
    }
    res = classify_availability_intent_node(state)
    assert res["intent"] == "BOOKING_REQUEST"
    assert "cannot complete a booking" in res["response"]


def test_availability_intent_classification_medical_rejected():
    state: DoctorAvailabilityState = {
        "user_message": "Give me medicine for chest pain",
        "user_timezone": "UTC",
        "messages": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "metadata": {},
    }
    res = classify_availability_intent_node(state)
    assert res["intent"] == "OUT_OF_SCOPE"
    assert "cannot provide medical diagnoses" in res["response"]


# ---------------------------------------------------------------------------
# 5. Graph Workflow Tests (with Mock LLM)
# ---------------------------------------------------------------------------


class MockChatModelWithTools:
    def __init__(self, responses: List[AIMessage]):
        self.responses = responses
        self._index = 0

    def bind_tools(self, tools: List[Any]):
        return self

    def invoke(self, messages: List[Any]) -> AIMessage:
        response = self.responses[self._index]
        self._index = (self._index + 1) % len(self.responses)
        return response


def test_graph_valid_availability_search_flow(seeded_availability_services):
    ai_tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_available_slots",
                "args": {"doctor_name": "Ahmed"},
                "id": "call_avail_123",
            }
        ],
    )
    ai_final_answer = AIMessage(
        content="Dr. Ahmed Khan is available tomorrow at 10:00 AM."
    )

    mock_llm = MockChatModelWithTools([ai_tool_call, ai_final_answer])
    graph = build_doctor_availability_graph(llm=mock_llm)

    initial_state = {
        "user_message": "Show me Dr. Ahmed's slots tomorrow",
        "user_timezone": "UTC",
        "messages": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "metadata": {},
    }

    res = graph.invoke(initial_state)

    assert res["intent"] == "AVAILABILITY_SEARCH"
    assert res.get("tool_results") is not None
    assert res["tool_results"].total == 2
    assert "Dr. Ahmed Khan" in res["response"]


def test_graph_booking_request_rejected():
    graph = build_doctor_availability_graph()
    initial_state = {
        "user_message": "Book an appointment with Dr. Ahmed",
        "user_timezone": "UTC",
        "messages": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "metadata": {},
    }

    res = graph.invoke(initial_state)
    assert res["intent"] == "BOOKING_REQUEST"
    assert "cannot complete a booking" in res["response"]


# ---------------------------------------------------------------------------
# 6. FastAPI Route Integration Tests
# ---------------------------------------------------------------------------


client = TestClient(app)


def test_api_search_availability_endpoint_success(
    seeded_availability_services, monkeypatch
):
    ai_tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_available_slots",
                "args": {"doctor_name": "Ahmed"},
                "id": "call_api_avail",
            }
        ],
    )
    ai_final_answer = AIMessage(content="Found 2 slots available for Dr. Ahmed Khan.")
    mock_llm = MockChatModelWithTools([ai_tool_call, ai_final_answer])

    def mock_build_graph():
        return build_doctor_availability_graph(llm=mock_llm)

    monkeypatch.setattr(
        "app.api.routes.availability.build_doctor_availability_graph",
        mock_build_graph,
    )

    response = client.post(
        "/api/v1/availability/search",
        json={
            "message": "Is Dr. Ahmed free tomorrow?",
            "user_timezone": "Asia/Karachi",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Dr. Ahmed Khan" in data["message"]
    assert len(data["slots"]) == 2


def test_api_search_availability_endpoint_empty_message():
    response = client.post(
        "/api/v1/availability/search",
        json={"message": "   "},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 7. System Prompt Validation
# ---------------------------------------------------------------------------


def test_availability_system_prompt_contains_safety_rules():
    assert "ONLY check slot availability" in AVAILABILITY_SYSTEM_PROMPT
    assert "NEVER invent, fabricate, or assume" in AVAILABILITY_SYSTEM_PROMPT
    assert (
        "DO NOT confirm or claim that an appointment is booked"
        in AVAILABILITY_SYSTEM_PROMPT
    )
    assert "DO NOT attempt to book, reschedule, or cancel" in AVAILABILITY_SYSTEM_PROMPT
    assert "DO NOT provide medical advice" in AVAILABILITY_SYSTEM_PROMPT
    assert "DO NOT write or execute raw SQL" in AVAILABILITY_SYSTEM_PROMPT
