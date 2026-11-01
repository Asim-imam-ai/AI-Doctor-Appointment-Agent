"""Health endpoint handler."""

from fastapi import APIRouter

from app.api.schemas.common import HealthCheckResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Check if service is operational.",
)
async def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(status="ok", service="doctor-appointment-agent")
