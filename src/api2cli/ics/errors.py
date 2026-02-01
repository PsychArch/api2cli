"""Error types for iCalendar operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ICSError(Exception):
    message: str
    code: str = "ICS_ERROR"
    details: Any | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


class ICSValidationError(ICSError):
    def __init__(self, message: str, field: str | None = None, value: Any | None = None) -> None:
        super().__init__(message, code="VALIDATION_ERROR", details={"field": field, "value": value})
        self.field = field
        self.value = value


class ICSFileError(ICSError):
    def __init__(self, message: str, path: str | None = None) -> None:
        super().__init__(message, code="FILE_ERROR", details={"path": path})
        self.path = path


class ICSEventNotFoundError(ICSError):
    def __init__(self, message: str, uid: str | None = None) -> None:
        super().__init__(message, code="NOT_FOUND", details={"uid": uid})
        self.uid = uid


def format_error_for_user(error: Exception) -> str:
    if isinstance(error, ICSValidationError):
        return f"Validation Error: {error.message}"
    if isinstance(error, ICSFileError):
        return f"File Error: {error.message}"
    if isinstance(error, ICSEventNotFoundError):
        return f"Not Found: {error.message}"
    if isinstance(error, ICSError):
        return f"Error: {error.message}"
    return f"Error: {str(error)}"
