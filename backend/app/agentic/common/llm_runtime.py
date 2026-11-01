"""Shared, lazily initialized OpenAI chat runtime."""

import os
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.core.config import settings


@lru_cache(maxsize=1)
def get_chat_model() -> ChatOpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required for agent execution.")
    if settings.LANGCHAIN_TRACING_V2:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
        if settings.LANGCHAIN_API_KEY:
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.0,
        timeout=settings.OPENAI_REQUEST_TIMEOUT_SECONDS,
        max_retries=settings.OPENAI_MAX_RETRIES,
    )
