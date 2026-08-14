"""Unit, graph, API, and tool safety tests for Phase 3 Doctor Discovery Agent."""

from typing import Any, List

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.agents import DoctorDiscoveryState, build_doctor_discovery_graph
from app.agents.doctor_discovery import (
    classify_intent_node,
)
from app.core.prompts import DOCTOR_DISCOVERY_SYSTEM_PROMPT
from app.main import app
from app.repositories import get_doctor_repository, get_specialty_repository
from app.schemas.doctor_discovery import (
    DoctorSearchCriteria,
    DoctorSearchResult,
)
from app.services import DoctorService
from app.tools import DOCTOR_DISCOVERY_TOOLS
from app.tools.doctor_search import (
    execute_doctor_search,
    get_doctor_details_tool,
    search_doctors_tool,
)


@pytest.fixture
def seeded_doctor_service():
    doc_repo = get_doctor_repository()
    spec_repo = get_specialty_repository()

    # Clear previous in-memory state if applicable
    if hasattr(doc_repo, "_storage"):
        doc_repo._storage.clear()
    if hasattr(doc_repo, "_doctor_specialties"):
        doc_repo._doctor_specialties.clear()
    if hasattr(spec_repo, "_storage"):
        spec_repo._storage.clear()

    service = DoctorService(doctor_repo=doc_repo, specialty_repo=spec_repo)

    d1 = service.register_doctor(
        name="Dr. Sarah Khan",
        bio="Senior Cardiologist",
        clinic_name="Heart Care Center",
        location="Lahore",
    )
    service.add_specialty_to_doctor(d1.id, "Cardiology")

    d2 = service.register_doctor(
        name="Dr. Ali Raza",
        bio="Dermatologist",
        clinic_name="Skin Care Clinic",
        location="Karachi",
    )
    service.add_specialty_to_doctor(d2.id, "Dermatology")

    d3 = service.register_doctor(
        name="Dr. Ayesha Ahmed",
        bio="Female General Dermatologist",
        clinic_name="Aesthetics Center",
        location="Lahore",
    )
    service.add_specialty_to_doctor(d3.id, "Dermatology")

    return service


# ---------------------------------------------------------------------------
# 1. Schema & Criteria Unit Tests
# ---------------------------------------------------------------------------


def test_doctor_search_criteria_defaults():
    criteria = DoctorSearchCriteria()
    assert criteria.specialty is None
    assert criteria.doctor_name is None
    assert criteria.is_active is True
    assert criteria.limit == 10


def test_doctor_search_criteria_validation():
    criteria = DoctorSearchCriteria(specialty="Cardiology", limit=5)
    assert criteria.specialty == "Cardiology"
    assert criteria.limit == 5


# ---------------------------------------------------------------------------
# 2. Tool & Service Integration Tests
# ---------------------------------------------------------------------------


def test_execute_doctor_search_specialty_filter(seeded_doctor_service):
    criteria = DoctorSearchCriteria(specialty="Cardiology")
    result = execute_doctor_search(criteria, doctor_service=seeded_doctor_service)

    assert isinstance(result, DoctorSearchResult)
    assert result.total == 1
    assert result.doctors[0].name == "Dr. Sarah Khan"
    assert "Cardiology" in result.doctors[0].specialties


def test_execute_doctor_search_location_and_specialty(seeded_doctor_service):
    criteria = DoctorSearchCriteria(specialty="Dermatology", location="Lahore")
    result = execute_doctor_search(criteria, doctor_service=seeded_doctor_service)

    assert result.total == 1
    assert result.doctors[0].name == "Dr. Ayesha Ahmed"


def test_execute_doctor_search_no_results(seeded_doctor_service):
    criteria = DoctorSearchCriteria(specialty="Neurology")
    result = execute_doctor_search(criteria, doctor_service=seeded_doctor_service)

    assert result.total == 0
    assert len(result.doctors) == 0


def test_search_doctors_tool_invocation(seeded_doctor_service):
    tool_output = search_doctors_tool.invoke({"specialty": "Cardiology"})
    assert isinstance(tool_output, str)
    assert "Dr. Sarah Khan" in tool_output


def test_get_doctor_details_tool_invocation(seeded_doctor_service):
    doctors = seeded_doctor_service.list_active_doctors()
    doc_id = str(doctors[0].id)

    tool_output = get_doctor_details_tool.invoke({"doctor_id": doc_id})
    assert isinstance(tool_output, str)
    assert doc_id in tool_output


def test_get_doctor_details_tool_invalid_uuid():
    tool_output = get_doctor_details_tool.invoke({"doctor_id": "invalid-uuid"})
    assert "Invalid UUID" in tool_output


# ---------------------------------------------------------------------------
# 3. Tool Allowlist & Safety Tests
# ---------------------------------------------------------------------------


def test_tool_allowlist_contains_only_read_only_tools():
    tool_names = [tool.name for tool in DOCTOR_DISCOVERY_TOOLS]
    assert "search_doctors" in tool_names
    assert "get_doctor_details" in tool_names

    # Ensure prohibited capabilities are not present
    prohibited = [
        "book_appointment",
        "cancel_appointment",
        "reschedule",
        "execute_sql",
        "send_email",
    ]
    for name in tool_names:
        assert name not in prohibited


# ---------------------------------------------------------------------------
# 4. Intent Classification & Safety Boundary Tests
# ---------------------------------------------------------------------------


def test_intent_classification_valid_search():
    state: DoctorDiscoveryState = {
        "user_message": "Find me a cardiologist in Lahore",
        "messages": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "metadata": {},
    }
    result = classify_intent_node(state)
    assert result["intent"] == "DOCTOR_SEARCH"


def test_intent_classification_medical_diagnosis_rejected():
    state: DoctorDiscoveryState = {
        "user_message": "I have severe chest pain, give me a diagnosis and medicine.",
        "messages": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "metadata": {},
    }
    result = classify_intent_node(state)
    assert result["intent"] == "OUT_OF_SCOPE"
    assert (
        "cannot provide medical" in result["response"].lower()
        or "cannot bypass safety rules" in result["response"].lower()
    )


def test_intent_classification_unsupported_booking_rejected():
    state: DoctorDiscoveryState = {
        "user_message": "Book an appointment with Dr. Sarah tomorrow at 10am.",
        "messages": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "metadata": {},
    }
    result = classify_intent_node(state)
    assert result["intent"] == "UNSUPPORTED"
    assert "cannot book" in result["response"]


# ---------------------------------------------------------------------------
# 5. LangGraph Workflow Tests (with Mocked Chat Model)
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


def test_graph_valid_doctor_search_flow(seeded_doctor_service):
    # Simulated LLM: First returns tool call, then returns formatted answer
    ai_tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_doctors",
                "args": {"specialty": "Cardiology"},
                "id": "call_123",
            }
        ],
    )
    ai_final_answer = AIMessage(
        content=(
            "I found Dr. Sarah Khan, a Senior Cardiologist at Heart Care "
            "Center in Lahore."
        )
    )

    mock_llm = MockChatModelWithTools([ai_tool_call, ai_final_answer])
    graph = build_doctor_discovery_graph(llm=mock_llm)

    initial_state = {
        "user_message": "Find me a cardiologist",
        "messages": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "metadata": {},
    }

    res = graph.invoke(initial_state)

    assert res["intent"] == "DOCTOR_SEARCH"
    assert res.get("tool_results") is not None
    assert res["tool_results"].total == 1
    assert "Dr. Sarah Khan" in res["response"]


def test_graph_unsupported_booking_request_flow():
    graph = build_doctor_discovery_graph()
    initial_state = {
        "user_message": "Book Dr. Sarah Khan for tomorrow",
        "messages": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "metadata": {},
    }

    res = graph.invoke(initial_state)
    assert res["intent"] == "UNSUPPORTED"
    assert "cannot book" in res["response"]


def test_graph_out_of_scope_diagnosis_flow():
    graph = build_doctor_discovery_graph()
    initial_state = {
        "user_message": "What medicine should I take for skin pain?",
        "messages": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "metadata": {},
    }

    res = graph.invoke(initial_state)
    assert res["intent"] == "OUT_OF_SCOPE"
    assert (
        "cannot provide medical" in res["response"].lower()
        or "healthcare provider" in res["response"].lower()
    )


def test_graph_iteration_limit_protection():
    # LLM that repeatedly calls tool beyond max limits
    infinite_tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_doctors",
                "args": {"specialty": "Cardiology"},
                "id": "call_loop",
            }
        ],
    )
    mock_llm = MockChatModelWithTools([infinite_tool_call])
    graph = build_doctor_discovery_graph(llm=mock_llm)

    initial_state = {
        "user_message": "Find me a cardiologist",
        "messages": [],
        "iteration_count": 5,
        "tool_call_count": 0,
        "metadata": {},
    }

    res = graph.invoke(initial_state)
    assert res.get("error") is not None
    assert "limit" in res["error"].lower() or "iteration" in res["error"].lower()


# ---------------------------------------------------------------------------
# 6. FastAPI Route Integration Tests
# ---------------------------------------------------------------------------


client = TestClient(app)


def test_api_search_doctors_endpoint_success(seeded_doctor_service, monkeypatch):
    ai_tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_doctors",
                "args": {"specialty": "Cardiology"},
                "id": "call_api",
            }
        ],
    )
    ai_final_answer = AIMessage(content="I found Dr. Sarah Khan matching Cardiology.")
    mock_llm = MockChatModelWithTools([ai_tool_call, ai_final_answer])

    def mock_build_graph():
        return build_doctor_discovery_graph(llm=mock_llm)

    monkeypatch.setattr(
        "app.api.routes.doctors.build_doctor_discovery_graph", mock_build_graph
    )

    response = client.post(
        "/api/v1/doctors/search",
        json={"message": "Find me a cardiologist"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Dr. Sarah Khan" in data["message"]
    assert len(data["doctors"]) == 1
    assert data["doctors"][0]["name"] == "Dr. Sarah Khan"


def test_api_search_doctors_endpoint_unsupported_request():
    response = client.post(
        "/api/v1/doctors/search",
        json={"message": "Book an appointment for me"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "cannot book" in data["message"]


def test_api_search_doctors_endpoint_empty_message():
    response = client.post(
        "/api/v1/doctors/search",
        json={"message": "   "},
    )
    assert response.status_code == 400
    assert "message cannot be empty" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 7. Prompt Validation Tests
# ---------------------------------------------------------------------------


def test_system_prompt_contains_safety_rules():
    assert "ONLY search for doctors using" in DOCTOR_DISCOVERY_SYSTEM_PROMPT
    assert "NEVER invent or hallucinate" in DOCTOR_DISCOVERY_SYSTEM_PROMPT
    assert (
        "DO NOT claim that a doctor has specific appointment availability"
        in DOCTOR_DISCOVERY_SYSTEM_PROMPT
    )
    assert (
        "DO NOT attempt to book, reschedule, or cancel"
        in DOCTOR_DISCOVERY_SYSTEM_PROMPT
    )
    assert "DO NOT provide medical diagnoses" in DOCTOR_DISCOVERY_SYSTEM_PROMPT
    assert (
        "DO NOT write, construct, or execute raw SQL queries"
        in DOCTOR_DISCOVERY_SYSTEM_PROMPT
    )
