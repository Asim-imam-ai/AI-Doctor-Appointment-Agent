"""Process-wide Supabase client for trusted backend operations."""

from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from app.core.config import settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Return the configured backend client or fail closed when configuration is absent."""
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not url or not key:
        raise RuntimeError("Supabase backend credentials are not configured.")
    try:
        return create_client(url, key)
    except Exception as exc:
        raise RuntimeError("Could not initialize the Supabase backend client.") from exc


def response_data(response: Any) -> list[dict[str, Any]]:
    """Normalize PostgREST and RPC response records."""
    data = getattr(response, "data", None)
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return []
