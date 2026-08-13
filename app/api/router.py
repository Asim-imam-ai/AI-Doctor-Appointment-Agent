"""Central API Router for v1 endpoints."""

from fastapi import APIRouter

from app.api.routes import doctors, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(doctors.router, prefix="/doctors", tags=["Doctors"])
