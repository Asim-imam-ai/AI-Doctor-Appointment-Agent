from fastapi import APIRouter

from app.api.v1 import (
    appointments,
    approvals,
    availability,
    chat,
    conversations,
    doctors,
    health,
    knowledge,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["Approvals"])
api_router.include_router(doctors.router, prefix="/doctors", tags=["Doctors"])
api_router.include_router(
    availability.router, prefix="/availability", tags=["Availability"]
)
api_router.include_router(
    appointments.router, prefix="/appointments", tags=["Appointments"]
)
api_router.include_router(
    conversations.router, prefix="/conversations", tags=["Conversations & Memory"]
)
api_router.include_router(
    knowledge.router, prefix="/knowledge", tags=["Knowledge Base & RAG"]
)
