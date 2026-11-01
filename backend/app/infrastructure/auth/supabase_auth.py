"""Supabase Auth token verification integration."""

from typing import Any
from uuid import UUID

from app.core.security import validate_supabase_claims
from app.infrastructure.db.supabase import get_supabase_client


def verify_access_token(token: str) -> tuple[Any, dict[str, Any]]:
    """Have Supabase verify the JWT signature, then validate project claims."""
    user = get_supabase_client().auth.get_user(token).user
    claims = validate_supabase_claims(token)
    if user is None or UUID(str(user.id)) != UUID(claims["sub"]):
        raise ValueError("Supabase token subject does not match the verified user.")
    return user, claims
