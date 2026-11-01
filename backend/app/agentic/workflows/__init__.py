"""Lazy public exports for independent workflow graph constructors."""

from importlib import import_module

_EXPORTS = {
    "build_doctor_discovery_graph": (
        "doctor_discovery.graph",
        "build_doctor_discovery_graph",
    ),
    "build_doctor_availability_graph": (
        "availability.graph",
        "build_doctor_availability_graph",
    ),
    "build_appointment_booking_graph": (
        "booking.graph",
        "build_appointment_booking_graph",
    ),
    "build_appointment_cancellation_graph": (
        "cancellation.graph",
        "build_appointment_cancellation_graph",
    ),
    "build_appointment_rescheduling_graph": (
        "rescheduling.graph",
        "build_appointment_rescheduling_graph",
    ),
    "DoctorDiscoveryState": ("doctor_discovery.state", "DoctorDiscoveryState"),
    "DoctorAvailabilityState": ("availability.state", "DoctorAvailabilityState"),
    "AppointmentBookingState": ("booking.state", "AppointmentBookingState"),
    "AppointmentCancellationState": (
        "cancellation.state",
        "AppointmentCancellationState",
    ),
    "AppointmentReschedulingState": (
        "rescheduling.state",
        "AppointmentReschedulingState",
    ),
    "classify_intent_node": ("doctor_discovery.nodes", "classify_intent_node"),
    "classify_availability_intent_node": (
        "availability.nodes",
        "classify_availability_intent_node",
    ),
    "classify_booking_intent_node": (
        "booking.nodes",
        "classify_booking_intent_node",
    ),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module, symbol = _EXPORTS[name]
    return getattr(import_module(f"{__name__}.{module}"), symbol)


__all__ = list(_EXPORTS)
