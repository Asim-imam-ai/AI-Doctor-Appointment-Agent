from fastapi import APIRouter

from app.api.routes import (
    appointments,
    availability,
    conversations,
    doctors,
    health,
    knowledge,
    notifications,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(doctors.router, prefix="/doctors", tags=["Doctors"])
api_router.include_router(
    availability.router, prefix="/availability", tags=["Availability"]
)
api_router.include_router(
    appointments.router, prefix="/appointments", tags=["Appointments"]
)
api_router.include_router(
    notifications.router, prefix="/notifications", tags=["Notifications & Reminders"]
)
api_router.include_router(
    conversations.router, prefix="/conversations", tags=["Conversations & Memory"]
)
api_router.include_router(
    knowledge.router, prefix="/knowledge", tags=["Knowledge Base & RAG"]
)
