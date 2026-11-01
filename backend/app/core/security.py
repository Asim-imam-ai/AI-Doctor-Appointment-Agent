"""JWT claim checks performed after Supabase Auth validates the signature."""

from datetime import datetime, timezone
from typing import Any

import jwt

from app.core.config import settings


def validate_supabase_claims(token: str) -> dict[str, Any]:
    """Decode and validate project issuer, audience, expiration, and subject.

    Signature verification is delegated to Supabase Auth so project key rotation
    remains managed by the configured Supabase project.
    """
    claims = jwt.decode(
        token,
        options={
            "verify_signature": False,
            "verify_exp": False,
            "verify_aud": False,
            "verify_iss": False,
        },
    )
    issuer = f"{(settings.SUPABASE_URL or '').rstrip('/')}/auth/v1"
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    expires_at = claims.get("exp")
    if (
        not settings.SUPABASE_URL
        or claims.get("iss") != issuer
        or settings.SUPABASE_JWT_AUDIENCE not in audiences
        or not isinstance(expires_at, (int, float))
        or expires_at <= datetime.now(timezone.utc).timestamp()
        or not isinstance(claims.get("sub"), str)
    ):
        raise ValueError("Supabase token claims are invalid.")
    return claims
