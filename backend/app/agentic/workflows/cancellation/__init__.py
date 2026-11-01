"""Cancellation graph, state, tools, and prompt."""

from importlib import import_module

_exports = {
    "build_appointment_cancellation_graph": (
        "graph",
        "build_appointment_cancellation_graph",
    ),
    "AppointmentCancellationState": ("state", "AppointmentCancellationState"),
}


def __getattr__(name):
    if name not in _exports:
        raise AttributeError(name)
    module, symbol = _exports[name]
    return getattr(import_module(f"{__name__}.{module}"), symbol)


__all__ = list(_exports)
