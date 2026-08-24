"""Custom exceptions for SMZDM Bot."""

from typing import Any


class SmzdmError(Exception):
    """Base exception for all SMZDM Bot errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(SmzdmError):
    """Configuration error (missing values, invalid format)."""


class APIError(SmzdmError):
    """API request failed."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message, details)

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"HTTP {self.status_code}")
        if self.error_code:
            parts.append(f"Code: {self.error_code}")
        if self.details:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)


# Alias for backward compatibility
AuthenticationError = APIError
