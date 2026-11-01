"""Shared initialization for PostgREST adapters."""


class SupabaseRepository:
    def __init__(self, client: object) -> None:
        if client is None:
            raise RuntimeError("A configured Supabase client is required.")
        self.client = client
