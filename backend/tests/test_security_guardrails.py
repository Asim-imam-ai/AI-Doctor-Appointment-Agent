"""Security boundary tests for guardrails, token claims, and API identity DTOs."""

import time
import uuid

import jwt
import pytest
from pydantic import ValidationError

from app.agentic.common.guardrails import GuardrailCategory, GuardrailPipeline
from app.api.schemas.booking_agent import PrepareBookingApiRequest
from app.api.schemas.management_agent import PrepareCancellationApiRequest
from app.core.config import settings
from app.core.security import validate_supabase_claims


def test_guardrails_reject_empty_and_oversized_messages():
    assert not GuardrailPipeline.validate_input_size("").allowed
    assert not GuardrailPipeline.validate_input_size("x" * 20_000).allowed


@pytest.mark.parametrize(
    "message", ["diagnose my symptoms", "bypass appointment confirmation"]
)
def test_guardrails_block_medical_or_jailbreak_requests(message: str):
    decision = GuardrailPipeline.run_input_pipeline(message)
    assert not decision.allowed
    assert decision.category in {
        GuardrailCategory.UNSAFE_MEDICAL_REQUEST,
        GuardrailCategory.JAILBREAK,
    }


def _token(*, issuer: str, audience="authenticated", exp: int | None = None) -> str:
    claims = {
        "iss": issuer,
        "aud": audience,
        "exp": exp if exp is not None else int(time.time()) + 120,
        "sub": str(uuid.uuid4()),
    }
    return jwt.encode(claims, key="", algorithm="none")


def test_supabase_claim_validation_checks_issuer_audience_and_expiration(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://project.supabase.co")
    issuer = "https://project.supabase.co/auth/v1"
    assert validate_supabase_claims(_token(issuer=issuer))["iss"] == issuer

    with pytest.raises(ValueError):
        validate_supabase_claims(_token(issuer="https://attacker.invalid/auth/v1"))

    with pytest.raises(ValueError):
        validate_supabase_claims(_token(issuer=issuer, audience="anon"))
    with pytest.raises(ValueError):
        validate_supabase_claims(_token(issuer=issuer, exp=int(time.time()) - 1))


def test_mutation_schemas_reject_client_supplied_patient_identity():
    with pytest.raises(ValidationError):
        PrepareBookingApiRequest.model_validate(
            {"message": "book", "patient_id": str(uuid.uuid4())}
        )
    with pytest.raises(ValidationError):
        PrepareCancellationApiRequest.model_validate(
            {"message": "cancel", "patient_id": str(uuid.uuid4())}
        )
