"""Validation and parsing helpers for iCalendar CLI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo
from pathlib import Path
from typing import Optional

from .config import local_timezone, resolve_calendar_path, resolve_timezone
from .constants import DEFAULT_CALENDAR_NAME
from .errors import ICSValidationError


@dataclass(frozen=True)
class CalendarCreateParams:
    path: Path
    name: str
    force: bool


@dataclass(frozen=True)
class EventCreateParams:
    path: Path
    summary: str
    start: date | datetime
    end: date | datetime | None
    all_day: bool
    description: Optional[str]
    location: Optional[str]


@dataclass(frozen=True)
class EventListParams:
    path: Path
    range_start: Optional[datetime]
    range_end: Optional[datetime]
    query: Optional[str]


def validate_calendar_create_params(
    path: Optional[Path],
    name: Optional[str],
    force: bool,
) -> CalendarCreateParams:
    resolved_path = resolve_calendar_path(path)
    calendar_name = (name or "").strip() or DEFAULT_CALENDAR_NAME
    return CalendarCreateParams(path=resolved_path, name=calendar_name, force=force)


def validate_calendar_path(path: Optional[Path]) -> Path:
    return resolve_calendar_path(path)


def validate_uid(uid: str) -> str:
    if not uid:
        raise ICSValidationError("UID is required", field="uid")
    return uid


def validate_timezone(tzid: Optional[str]) -> Optional[tuple[tzinfo, str]]:
    if tzid is None:
        return None
    try:
        return resolve_timezone(tzid)
    except ValueError as exc:
        raise ICSValidationError(
            "Invalid timezone. Use an IANA name like America/Los_Angeles or UTC.",
            field="tz",
            value=tzid,
        ) from exc


def validate_summary(summary: str) -> str:
    if not summary:
        raise ICSValidationError("Summary is required", field="summary")
    return summary


def parse_event_datetime(value: str, all_day: bool, tz: tzinfo) -> date | datetime:
    if not value:
        raise ICSValidationError("Date/time value is required", field="datetime")

    if all_day:
        try:
            return date.fromisoformat(value)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError as exc:
                raise ICSValidationError(
                    "Invalid date format. Use YYYY-MM-DD for all-day events",
                    field="datetime",
                    value=value,
                ) from exc
            return parsed.date()

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        try:
            parsed_date = date.fromisoformat(value)
        except ValueError as exc:
            raise ICSValidationError(
                "Invalid datetime format. Use ISO 8601 (e.g. 2026-02-01T09:00)",
                field="datetime",
                value=value,
            ) from exc
        parsed = datetime.combine(parsed_date, time.min)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed


def normalize_event_end(
    start: date | datetime,
    end: Optional[date | datetime],
    all_day: bool,
    tz: tzinfo,
) -> Optional[date | datetime]:
    if end is None:
        if all_day:
            return start + timedelta(days=1)  # type: ignore[operator]
        return None

    if all_day and isinstance(end, datetime):
        end = end.date()
    if not all_day and isinstance(end, date) and not isinstance(end, datetime):
        end = datetime.combine(end, time.min, tzinfo=tz)
    return end


def validate_start_end(
    start: date | datetime,
    end: Optional[date | datetime],
    all_day: bool,
    end_inclusive: bool = False,
) -> None:
    if end is None:
        return

    if all_day:
        start_date = start if isinstance(start, date) and not isinstance(start, datetime) else start.date()
        end_date = end if isinstance(end, date) and not isinstance(end, datetime) else end.date()
        if end_inclusive:
            if end_date < start_date:
                raise ICSValidationError("End date must not be before start date", field="end")
        else:
            if end_date <= start_date:
                raise ICSValidationError("End date must be after start date", field="end")
        return

    start_dt = start if isinstance(start, datetime) else datetime.combine(start, time.min)
    end_dt = end if isinstance(end, datetime) else datetime.combine(end, time.min)
    if end_dt < start_dt:
        raise ICSValidationError("End time must not be before start time", field="end")


def parse_event_range(
    range_start: Optional[str],
    range_end: Optional[str],
    tz: Optional[tzinfo] = None,
) -> tuple[Optional[datetime], Optional[datetime]]:
    tzinfo = tz or local_timezone()

    def parse_range_value(value: str, is_end: bool) -> datetime:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            try:
                parsed_date = date.fromisoformat(value)
            except ValueError as exc:
                raise ICSValidationError(
                    "Invalid range value. Use ISO 8601 date or datetime",
                    field="range",
                    value=value,
                ) from exc
            parsed = datetime.combine(
                parsed_date,
                time.max if is_end else time.min,
                tzinfo=tzinfo,
            )
        else:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=tzinfo)
        return parsed

    start_value = parse_range_value(range_start, is_end=False) if range_start else None
    end_value = parse_range_value(range_end, is_end=True) if range_end else None
    if start_value and end_value and end_value < start_value:
        raise ICSValidationError("Range end must not be before range start", field="range")
    return start_value, end_value


def validate_list_params(
    path: Optional[Path],
    range_start: Optional[str],
    range_end: Optional[str],
    query: Optional[str],
    tz: Optional[tzinfo] = None,
) -> EventListParams:
    resolved_path = resolve_calendar_path(path)
    parsed_start, parsed_end = parse_event_range(range_start, range_end, tz=tz)
    cleaned_query = query.strip() if query else None
    return EventListParams(path=resolved_path, range_start=parsed_start, range_end=parsed_end, query=cleaned_query)


def validate_create_params(
    path: Optional[Path],
    summary: str,
    start: str,
    end: Optional[str],
    all_day: bool,
    description: Optional[str],
    location: Optional[str],
    tz: Optional[tzinfo] = None,
) -> EventCreateParams:
    resolved_path = resolve_calendar_path(path)
    validated_summary = validate_summary(summary)
    tzinfo = tz or local_timezone()
    parsed_start = parse_event_datetime(start, all_day=all_day, tz=tzinfo)
    parsed_end = parse_event_datetime(end, all_day=all_day, tz=tzinfo) if end else None
    if all_day and parsed_end is not None:
        validate_start_end(parsed_start, parsed_end, all_day=True, end_inclusive=True)
        parsed_end = parsed_end + timedelta(days=1)
    normalized_end = normalize_event_end(parsed_start, parsed_end, all_day=all_day, tz=tzinfo)
    validate_start_end(parsed_start, normalized_end, all_day=all_day)

    return EventCreateParams(
        path=resolved_path,
        summary=validated_summary,
        start=parsed_start,
        end=normalized_end,
        all_day=all_day,
        description=description,
        location=location,
    )
