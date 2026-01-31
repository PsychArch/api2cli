"""Error types for Jina integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class JinaError(Exception):
    message: str
    code: str = "JINA_ERROR"
    details: Any | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


class JinaConfigError(JinaError):
    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message, code="CONFIG_ERROR", details=details)


class JinaAPIError(JinaError):
    def __init__(self, message: str, status_code: int | None = None, response: Any | None = None) -> None:
        super().__init__(message, code="API_ERROR", details={"status_code": status_code, "response": response})
        self.status_code = status_code
        self.response = response


class JinaValidationError(JinaError):
    def __init__(self, message: str, field: str | None = None, value: Any | None = None) -> None:
        super().__init__(message, code="VALIDATION_ERROR", details={"field": field, "value": value})
        self.field = field
        self.value = value


class JinaNetworkError(JinaError):
    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message, code="NETWORK_ERROR", details={"original_error": str(original_error) if original_error else None})
        self.original_error = original_error


class JinaTimeoutError(JinaError):
    def __init__(self, message: str, timeout: float | None = None) -> None:
        super().__init__(message, code="TIMEOUT_ERROR", details={"timeout": timeout})
        self.timeout = timeout


class JinaCacheError(JinaError):
    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message, code="CACHE_ERROR", details=details)


def format_error_for_user(error: Exception) -> str:
    if isinstance(error, JinaConfigError):
        return f"Configuration Error: {error.message}"
    if isinstance(error, JinaValidationError):
        return f"Validation Error: {error.message}"
    if isinstance(error, JinaAPIError):
        return f"API Error: {error.message}"
    if isinstance(error, JinaNetworkError):
        return f"Network Error: {error.message}"
    if isinstance(error, JinaTimeoutError):
        return f"Timeout Error: {error.message}"
    if isinstance(error, JinaCacheError):
        return f"Cache Error: {error.message}"
    return f"Error: {str(error)}"
