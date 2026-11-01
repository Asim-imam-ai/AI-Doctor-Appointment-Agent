"""Deterministic, low-risk intent routing for top-level chat requests."""

from enum import StrEnum


class Intent(StrEnum):
    DISCOVERY = "doctor_discovery"
    AVAILABILITY = "availability"
    BOOKING = "booking"
    CANCELLATION = "cancellation"
    RESCHEDULING = "rescheduling"
    KNOWLEDGE = "knowledge"
    CLARIFY = "clarify"


def classify_intent(message: str) -> Intent:
    text = message.casefold()
    groups = {
        Intent.CANCELLATION: ("cancel", "cancellation"),
        Intent.RESCHEDULING: (
            "reschedule",
            "change my appointment",
            "move my appointment",
        ),
        Intent.BOOKING: ("book", "schedule an appointment", "make an appointment"),
        Intent.AVAILABILITY: ("available", "availability", "open slot", "time slot"),
        Intent.DISCOVERY: ("doctor", "specialist", "physician", "cardiologist"),
        Intent.KNOWLEDGE: ("policy", "clinic hours", "insurance", "how does"),
    }
    matches = [
        intent
        for intent, words in groups.items()
        if any(word in text for word in words)
    ]
    return matches[0] if len(matches) == 1 else Intent.CLARIFY
