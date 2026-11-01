"""Doctor discovery schema, tool, graph, and safety unit tests."""

from unittest.mock import Mock

from app.agentic.common.tool_executor import DOCTOR_DISCOVERY_TOOLS
from app.agentic.workflows.doctor_discovery.graph import build_doctor_discovery_graph
from app.agentic.workflows.doctor_discovery.nodes import classify_intent_node
from app.agentic.workflows.doctor_discovery.prompts import (
    DOCTOR_DISCOVERY_SYSTEM_PROMPT,
)
from app.agentic.workflows.doctor_discovery.tools import execute_doctor_search
from app.api.schemas.doctor_discovery import DoctorSearchCriteria
from app.domain.models import DoctorModel


def test_search_criteria_defaults():
    criteria = DoctorSearchCriteria(location="Lahore")
    assert criteria.specialty is None
    assert criteria.location == "Lahore"


def test_execute_doctor_search_delegates_filters():
    service = Mock()
    expected = [DoctorModel(name="Dr. Khan")]
    service.search_doctors.return_value = expected
    service.get_doctor_specialties.return_value = []
    result = execute_doctor_search(
        DoctorSearchCriteria(specialty="Cardiology", location="Lahore"),
        doctor_service=service,
    )
    assert result.total == 1
    assert result.doctors[0].name == "Dr. Khan"
    service.search_doctors.assert_called_once()


def test_doctor_tool_allowlist_is_read_only():
    assert {tool.name for tool in DOCTOR_DISCOVERY_TOOLS} == {
        "search_doctors",
        "get_doctor_details",
    }


def test_intent_classifier_rejects_medical_diagnosis_and_mutations():
    assert (
        classify_intent_node({"user_message": "diagnose my chest pain"})["intent"]
        == "OUT_OF_SCOPE"
    )
    assert (
        classify_intent_node({"user_message": "book me an appointment"})["intent"]
        == "UNSUPPORTED"
    )


def test_discovery_graph_compiles_and_prompt_sets_boundary():
    graph = build_doctor_discovery_graph(llm=Mock())
    assert graph is not None
    assert "not provide medical" in DOCTOR_DISCOVERY_SYSTEM_PROMPT.lower()
