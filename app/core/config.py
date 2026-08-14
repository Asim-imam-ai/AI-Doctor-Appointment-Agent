from enum import Enum
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "doctor-appointment-agent"
    APP_ENV: Environment = Environment.DEVELOPMENT
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # LLM Settings (Future Phase setup)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"

    # LangChain / LangSmith Observability
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "doctor-appointment-agent"
    LANGCHAIN_TRACING_V2: bool = False

    # Database / Backend
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None

    # Policy Settings
    CANCELLATION_WINDOW_MINUTES: int = 120
    MAX_AGENT_ITERATIONS: int = 5


settings = Settings()
