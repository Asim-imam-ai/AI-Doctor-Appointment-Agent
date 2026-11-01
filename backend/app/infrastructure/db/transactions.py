"""Typed boundary for PostgreSQL RPCs that execute transactional operations."""

from typing import Any

from app.infrastructure.db.supabase import response_data


def execute_postgres_transaction(
    client: Any, function: str, parameters: dict[str, Any]
) -> dict[str, Any]:
    """Call one approved Postgres RPC and return its structured JSON result."""
    try:
        response = client.rpc(function, parameters).execute()
    except Exception as exc:
        raise RuntimeError("Atomic database operation failed.") from exc
    rows = response_data(response)
    result = rows[0] if rows else getattr(response, "data", None)
    if isinstance(result, dict) and isinstance(result.get("result"), dict):
        result = result["result"]
    if not isinstance(result, dict):
        raise RuntimeError(f"{function} returned an invalid database response.")
    return result
