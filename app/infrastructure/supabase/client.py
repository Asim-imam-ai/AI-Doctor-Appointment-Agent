"""Supabase client infrastructure module."""

import logging
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy loading / mock container for Supabase client
_supabase_client: Optional[Any] = None


def get_supabase_client() -> Optional[Any]:
    """Centralized retriever/initializer for the Supabase client.

    Returns None if credentials are not configured, preventing crash at startup.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning(
            "Supabase credentials (SUPABASE_URL/SUPABASE_KEY) not set. "
            "Client returned as None."
        )
        return None

    try:
        from supabase import create_client

        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None
