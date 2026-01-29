"""Error types for Minimax integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MinimaxError(Exception):
    message: str
    code: str = "MINIMAX_ERROR"
    details: Any | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


class MinimaxConfigError(MinimaxError):
    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message, code="CONFIG_ERROR", details=details)


class MinimaxAPIError(MinimaxError):
    def __init__(self, message: str, status_code: int | None = None, response: Any | None = None) -> None:
        super().__init__(message, code="API_ERROR", details={"status_code": status_code, "response": response})
        self.status_code = status_code
        self.response = response


class MinimaxValidationError(MinimaxError):
    def __init__(self, message: str, field: str | None = None, value: Any | None = None) -> None:
        super().__init__(message, code="VALIDATION_ERROR", details={"field": field, "value": value})
        self.field = field
        self.value = value


class MinimaxNetworkError(MinimaxError):
    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message, code="NETWORK_ERROR", details={"original_error": str(original_error) if original_error else None})
        self.original_error = original_error


class MinimaxTimeoutError(MinimaxError):
    def __init__(self, message: str, timeout: float | None = None) -> None:
        super().__init__(message, code="TIMEOUT_ERROR", details={"timeout": timeout})
        self.timeout = timeout


class MinimaxRateLimitError(MinimaxError):
    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message, code="RATE_LIMIT_ERROR", details={"retry_after": retry_after})
        self.retry_after = retry_after


def format_error_for_user(error: Exception) -> str:
    if isinstance(error, MinimaxConfigError):
        return f"Configuration Error: {error.message}"
    if isinstance(error, MinimaxValidationError):
        return f"Validation Error: {error.message}"
    if isinstance(error, MinimaxAPIError):
        return f"API Error: {error.message}"
    if isinstance(error, MinimaxNetworkError):
        return f"Network Error: {error.message}"
    if isinstance(error, MinimaxTimeoutError):
        return f"Timeout Error: {error.message}"
    if isinstance(error, MinimaxRateLimitError):
        return f"Rate Limit Error: {error.message}"
    return f"Error: {str(error)}"
