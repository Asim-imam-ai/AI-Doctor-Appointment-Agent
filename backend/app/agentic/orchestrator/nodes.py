"""Top-level orchestration node implementations."""

from typing import Any

from app.agentic.common.routing import Intent, classify_intent


def route_request(state: dict[str, Any]) -> dict[str, Any]:
    return {"intent": classify_intent(state.get("user_message", "")).value}


def clarify(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "response": "Would you like to find a doctor, check availability, book, cancel, reschedule, or ask about a clinic policy?"
    }


def dispatch(state: dict[str, Any]) -> dict[str, Any]:
    intent = Intent(state["intent"])
    constructors = {
        Intent.DISCOVERY: "app.agentic.workflows.doctor_discovery.graph:build_doctor_discovery_graph",
        Intent.AVAILABILITY: "app.agentic.workflows.availability.graph:build_doctor_availability_graph",
        Intent.BOOKING: "app.agentic.workflows.booking.graph:build_appointment_booking_graph",
        Intent.CANCELLATION: "app.agentic.workflows.cancellation.graph:build_appointment_cancellation_graph",
        Intent.RESCHEDULING: "app.agentic.workflows.rescheduling.graph:build_appointment_rescheduling_graph",
    }
    if intent == Intent.KNOWLEDGE:
        from app.infrastructure.db.services import get_rag_service

        answer = get_rag_service().answer_query(state["user_message"])
        return {"response": answer.answer, "result": answer.model_dump(mode="json")}
    module_name, function_name = constructors[intent].split(":")
    from importlib import import_module

    graph = getattr(import_module(module_name), function_name)()
    result = graph.invoke(
        {
            "user_message": state["user_message"],
            "patient_id": state.get("patient_id"),
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "metadata": {},
        }
    )
    return {
        "response": result.get("response", "I could not complete that request."),
        "result": {
            k: v.model_dump(mode="json") if hasattr(v, "model_dump") else v
            for k, v in result.items()
            if k.endswith("proposal") or k.endswith("result")
        },
        "error": result.get("error"),
    }
