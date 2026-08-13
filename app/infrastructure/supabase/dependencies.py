"""FastAPI dependencies for Supabase infrastructure."""

from typing import Optional

from app.infrastructure.supabase.client import get_supabase_client


def get_db_client() -> Optional[object]:
    """Dependency injector for Supabase DB client."""
    return get_supabase_client()
