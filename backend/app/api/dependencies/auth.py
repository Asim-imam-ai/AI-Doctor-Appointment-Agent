"""Supabase Auth bearer-token verification and patient identity resolution."""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.infrastructure.auth.supabase_auth import verify_access_token
from app.infrastructure.db.services import get_patient_service

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedIdentity:
    auth_user_id: UUID
    email: str | None
    role: str


@dataclass(frozen=True)
class AuthenticatedPatient:
    id: UUID
    auth_user_id: UUID
    email: str | None
    role: str


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="A valid Supabase access token is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedIdentity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    token = credentials.credentials
    try:
        # Supabase Auth verifies the token signature against the project's active
        # signing keys. Claims are checked locally after signature verification.
        user, _claims = verify_access_token(token)
        auth_user_id = UUID(str(user.id))
        app_metadata = getattr(user, "app_metadata", None) or {}
        role = str(app_metadata.get("role", "authenticated"))
        return AuthenticatedIdentity(
            auth_user_id=auth_user_id,
            email=getattr(user, "email", None),
            role=role,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise _unauthorized() from exc


async def get_current_patient(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> AuthenticatedPatient:
    profile_service = get_patient_service()
    patient = profile_service.get_by_external_id(str(identity.auth_user_id))
    if patient is None:
        patient = profile_service.get_patient(identity.auth_user_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No patient profile is linked to this account.",
        )
    return AuthenticatedPatient(
        id=patient.id,
        auth_user_id=identity.auth_user_id,
        email=identity.email,
        role=identity.role,
    )


async def require_admin(
    patient: AuthenticatedPatient = Depends(get_current_patient),
) -> AuthenticatedPatient:
    if patient.role.lower() not in {"admin", "superuser"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )
    return patient
