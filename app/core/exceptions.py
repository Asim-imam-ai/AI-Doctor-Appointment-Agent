"""Core custom exception classes."""

from typing import Any, Optional


class ApplicationError(Exception):
    """Base application exception."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ResourceNotFoundError(ApplicationError):
    """Raised when a requested resource is not found."""

    pass


class ValidationError(ApplicationError):
    """Raised when input validation fails."""

    pass


class SecurityError(ApplicationError):
    """Raised when security boundaries or checks fail."""

    pass
