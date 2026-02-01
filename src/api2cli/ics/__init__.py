"""iCalendar CRUD helpers."""

from .calendar import (
    EventInfo,
    add_event,
    calendar_timezone_for_path,
    create_calendar,
    delete_event,
    get_event,
    list_events,
    update_event,
)
from .config import default_calendar_path, resolve_calendar_path
from .errors import ICSError, ICSEventNotFoundError, ICSFileError, ICSValidationError, format_error_for_user
from .validators import (
    CalendarCreateParams,
    EventCreateParams,
    EventListParams,
    validate_calendar_create_params,
    validate_calendar_path,
    validate_create_params,
    validate_list_params,
    validate_summary,
    validate_timezone,
    validate_uid,
)

__all__ = [
    "EventInfo",
    "add_event",
    "create_calendar",
    "delete_event",
    "get_event",
    "list_events",
    "update_event",
    "calendar_timezone_for_path",
    "default_calendar_path",
    "resolve_calendar_path",
    "ICSError",
    "ICSEventNotFoundError",
    "ICSFileError",
    "ICSValidationError",
    "format_error_for_user",
    "CalendarCreateParams",
    "EventCreateParams",
    "EventListParams",
    "validate_calendar_create_params",
    "validate_calendar_path",
    "validate_create_params",
    "validate_list_params",
    "validate_summary",
    "validate_timezone",
    "validate_uid",
]
