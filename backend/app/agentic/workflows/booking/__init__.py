"""Booking graph, state, tools, and prompt."""

from importlib import import_module

_exports = {
    "build_appointment_booking_graph": ("graph", "build_appointment_booking_graph"),
    "AppointmentBookingState": ("state", "AppointmentBookingState"),
    "classify_booking_intent_node": ("nodes", "classify_booking_intent_node"),
}


def __getattr__(name):
    if name not in _exports:
        raise AttributeError(name)
    module, symbol = _exports[name]
    return getattr(import_module(f"{__name__}.{module}"), symbol)


__all__ = list(_exports)
