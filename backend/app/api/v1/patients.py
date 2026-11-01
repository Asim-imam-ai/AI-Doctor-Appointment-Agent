"""Authenticated patient onboarding and current profile."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.api.dependencies.auth import (
    AuthenticatedIdentity,
    AuthenticatedPatient,
    get_current_identity,
    get_current_patient,
)
from app.domain.patients.models import PatientModel
from app.infrastructure.db.services import get_patient_service

router = APIRouter()


class PatientSetupRequest(BaseModel):
    model_config = {"extra": "forbid"}
    name: str = Field(min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    timezone: str = Field(default="UTC", max_length=50)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 2:
            raise ValueError("Name must contain at least two characters.")
        return stripped


class CurrentPatientResponse(BaseModel):
    name: str
    email: str
    phone: str | None
    timezone: str


def _response(patient: PatientModel) -> CurrentPatientResponse:
    return CurrentPatientResponse(
        name=patient.name,
        email=patient.email,
        phone=patient.phone,
        timezone=patient.timezone,
    )


@router.get("/me", response_model=CurrentPatientResponse)
async def get_my_profile(
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    profile = get_patient_service().get_patient(patient.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
    return _response(profile)


@router.post("/me", response_model=CurrentPatientResponse, status_code=201)
async def setup_my_profile(
    request: PatientSetupRequest,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    if not identity.email:
        raise HTTPException(status_code=403, detail="An account email is required.")
    service = get_patient_service()
    existing = service.get_by_external_id(str(identity.auth_user_id))
    if existing is not None:
        return _response(existing)
    if service.get_by_email(identity.email) is not None:
        raise HTTPException(
            status_code=409, detail="Patient profile linking requires clinic support."
        )
    profile = service.register_patient(
        name=request.name.strip(),
        email=identity.email,
        phone=request.phone,
        external_user_id=str(identity.auth_user_id),
        timezone=request.timezone,
    )
    return _response(profile)
