"""Common schemas and response wrappers."""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class HealthCheckResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "service": "doctor-appointment-agent",
            }
        }
    )
    status: str = Field(default="ok")
    service: str = Field(default="doctor-appointment-agent")


class ResponseWrapper(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
