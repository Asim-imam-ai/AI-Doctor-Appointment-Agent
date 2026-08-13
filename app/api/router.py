"""Central API Router for v1 endpoints."""

from fastapi import APIRouter

from app.api.routes import appointments, availability, doctors, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(doctors.router, prefix="/doctors", tags=["Doctors"])
api_router.include_router(
    availability.router, prefix="/availability", tags=["Availability"]
)
api_router.include_router(
    appointments.router, prefix="/appointments", tags=["Appointments"]
)
