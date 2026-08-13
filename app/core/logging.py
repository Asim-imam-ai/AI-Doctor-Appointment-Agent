"""Centralized logging configuration."""

import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """Configure application logging strictly without exposing secrets or PII."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


logger = logging.getLogger("app")
