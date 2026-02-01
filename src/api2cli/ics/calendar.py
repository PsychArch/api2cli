"""Calendar CRUD helpers for .ics files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Optional
from uuid import uuid4

from icalendar import Calendar, Event, Timezone

from .config import calendar_timezone, local_timezone, resolve_calendar_path, resolve_timezone, tzinfo_for_tzid
from .constants import DEFAULT_CALENDAR_NAME, PROD_ID
from .errors import ICSFileError, ICSEventNotFoundError, ICSValidationError
from .validators import EventCreateParams, normalize_event_end, parse_event_datetime, validate_start_end


@dataclass(frozen=True)
class EventInfo:
    uid: str
    summary: str
    start: date | datetime
    end: date | datetime | None
    all_day: bool
    location: Optional[str]
    description: Optional[str]


def _build_calendar(name: str, tzid: Optional[str] = None) -> Calendar:
    calendar = Calendar()
    calendar.add("prodid", PROD_ID)
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("x-wr-calname", name)
    tzinfo_value, tzid_value = resolve_timezone(tzid)
    calendar.add("x-wr-timezone", tzid_value)
    try:
        calendar.add_component(Timezone.from_tzinfo(tzinfo_value, tzid=tzid_value))
    except ValueError:
        pass
    return calendar


def _ensure_parent_dir(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ICSFileError("Unable to create calendar directory", path=str(path)) from exc


def _load_calendar(path: Path) -> Calendar:
    if not path.exists():
        raise ICSFileError("Calendar file not found", path=str(path))
    if path.is_dir():
        raise ICSFileError("Calendar path is a directory", path=str(path))
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ICSFileError("Unable to read calendar file", path=str(path)) from exc
    try:
        return Calendar.from_ical(data)
    except Exception as exc:
        raise ICSValidationError("Invalid calendar file format") from exc


def _save_calendar(path: Path, calendar: Calendar) -> None:
    _ensure_parent_dir(path)
    try:
        path.write_bytes(calendar.to_ical())
    except OSError as exc:
        raise ICSFileError("Unable to write calendar file", path=str(path)) from exc


def create_calendar(
    path: Path,
    name: Optional[str] = None,
    force: bool = False,
    tzid: Optional[str] = None,
) -> Path:
    if path.exists():
        if path.is_dir():
            raise ICSFileError("Calendar path is a directory", path=str(path))
        if not force:
            raise ICSFileError("Calendar file already exists", path=str(path))
    calendar_name = name or DEFAULT_CALENDAR_NAME
    calendar = _build_calendar(calendar_name, tzid=tzid)
    _save_calendar(path, calendar)
    return path


def _ensure_calendar(path: Path, tzid: Optional[str] = None) -> Calendar:
    if path.exists():
        return _load_calendar(path)
    calendar = _build_calendar(DEFAULT_CALENDAR_NAME, tzid=tzid)
    _save_calendar(path, calendar)
    return calendar


def _calendar_tzid(calendar: Calendar) -> Optional[str]:
    tzid = calendar.get("x-wr-timezone")
    if tzid:
        return str(tzid)
    for component in calendar.walk("VTIMEZONE"):
        component_tzid = component.get("tzid")
        if component_tzid:
            return str(component_tzid)
    return None


def _calendar_timezone_for_parse(calendar: Calendar, tzid_override: Optional[str] = None) -> tzinfo:
    if tzid_override:
        return resolve_timezone(tzid_override)[0]
    tzid = _calendar_tzid(calendar)
    tzinfo_value = tzinfo_for_tzid(tzid)
    if tzinfo_value is not None:
        return tzinfo_value
    return local_timezone()


def _ensure_calendar_timezone(calendar: Calendar, tzid_override: Optional[str] = None) -> tzinfo:
    if tzid_override:
        tzinfo_value, tzid_value = resolve_timezone(tzid_override)
        if calendar.get("x-wr-timezone") is None:
            calendar.add("x-wr-timezone", tzid_value)
        else:
            calendar["x-wr-timezone"] = tzid_value
        has_vtimezone = False
        for component in calendar.walk("VTIMEZONE"):
            component_tzid = component.get("tzid")
            if component_tzid and str(component_tzid) == tzid_value:
                has_vtimezone = True
                break
        if not has_vtimezone:
            try:
                calendar.add_component(Timezone.from_tzinfo(tzinfo_value, tzid=tzid_value))
            except ValueError:
                pass
        return tzinfo_value

    tzid = _calendar_tzid(calendar)
    if not tzid:
        tzinfo_value, tzid_value = calendar_timezone()
        calendar.add("x-wr-timezone", tzid_value)
        try:
            calendar.add_component(Timezone.from_tzinfo(tzinfo_value, tzid=tzid_value))
        except ValueError:
            pass
        return tzinfo_value

    tzinfo_value = tzinfo_for_tzid(tzid)
    if calendar.get("x-wr-timezone") is None:
        calendar.add("x-wr-timezone", tzid)

    if tzinfo_value is not None:
        has_vtimezone = False
        for component in calendar.walk("VTIMEZONE"):
            component_tzid = component.get("tzid")
            if component_tzid and str(component_tzid) == tzid:
                has_vtimezone = True
                break
        if not has_vtimezone:
            try:
                calendar.add_component(Timezone.from_tzinfo(tzinfo_value, tzid=tzid))
            except ValueError:
                pass
        return tzinfo_value

    return local_timezone()


def _event_info(event: Event) -> EventInfo:
    uid = str(event.get("uid", ""))
    summary = str(event.get("summary", ""))
    start_prop = event.get("dtstart")
    if start_prop is None:
        raise ICSValidationError("Event is missing DTSTART")
    start_value = start_prop.dt
    end_prop = event.get("dtend")
    end_value = end_prop.dt if end_prop is not None else None
    all_day = isinstance(start_value, date) and not isinstance(start_value, datetime)
    location = str(event.get("location")) if event.get("location") is not None else None
    description = str(event.get("description")) if event.get("description") is not None else None
    return EventInfo(
        uid=uid,
        summary=summary,
        start=start_value,
        end=end_value,
        all_day=all_day,
        location=location,
        description=description,
    )


def _event_matches(
    info: EventInfo,
    range_start: Optional[datetime],
    range_end: Optional[datetime],
    query: Optional[str],
    tzinfo: tzinfo,
) -> bool:
    if query:
        haystack = " ".join(filter(None, [info.summary, info.description, info.location])).casefold()
        if query.casefold() not in haystack:
            return False

    def to_dt(value: date | datetime) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=tzinfo)
        return datetime.combine(value, time.min, tzinfo=tzinfo)

    start_dt = to_dt(info.start)
    end_value = info.end
    if end_value is None:
        end_dt = start_dt
    else:
        if isinstance(end_value, datetime):
            end_dt = end_value if end_value.tzinfo else end_value.replace(tzinfo=tzinfo)
        else:
            end_dt = datetime.combine(end_value, time.min, tzinfo=tzinfo)

    if range_start and end_dt < range_start:
        return False
    if range_end and start_dt > range_end:
        return False
    return True


def _event_sort_key(info: EventInfo, tzinfo: tzinfo) -> tuple[datetime, str]:
    if isinstance(info.start, datetime):
        start_dt = info.start if info.start.tzinfo else info.start.replace(tzinfo=tzinfo)
    else:
        start_dt = datetime.combine(info.start, time.min, tzinfo=tzinfo)
    return start_dt, info.uid


def list_events(
    path: Path,
    range_start: Optional[datetime] = None,
    range_end: Optional[datetime] = None,
    query: Optional[str] = None,
    tzinfo_override: Optional[tzinfo] = None,
) -> list[EventInfo]:
    calendar = _load_calendar(path)
    tzinfo = tzinfo_override or _calendar_timezone_for_parse(calendar)
    events: list[EventInfo] = []
    for component in calendar.walk("VEVENT"):
        info = _event_info(component)
        if _event_matches(info, range_start, range_end, query, tzinfo):
            events.append(info)
    events.sort(key=lambda info: _event_sort_key(info, tzinfo))
    return events


def get_event(path: Path, uid: str) -> EventInfo:
    calendar = _load_calendar(path)
    for component in calendar.walk("VEVENT"):
        info = _event_info(component)
        if info.uid == uid:
            return info
    raise ICSEventNotFoundError("Event not found", uid=uid)


def _find_event(calendar: Calendar, uid: str) -> Event:
    for component in calendar.walk("VEVENT"):
        if str(component.get("uid", "")) == uid:
            return component
    raise ICSEventNotFoundError("Event not found", uid=uid)


def add_event(params: EventCreateParams, tzid: Optional[str] = None) -> EventInfo:
    calendar = _ensure_calendar(params.path, tzid=tzid)
    tzinfo_value = _ensure_calendar_timezone(calendar, tzid_override=tzid)

    event = Event()
    uid = str(uuid4())
    event.add("uid", uid)
    event.add("summary", params.summary)
    start_value = params.start
    if isinstance(start_value, datetime) and start_value.tzinfo is None:
        start_value = start_value.replace(tzinfo=tzinfo_value)
    event.add("dtstart", start_value)
    if params.end is not None:
        end_value = params.end
        if isinstance(end_value, datetime) and end_value.tzinfo is None:
            end_value = end_value.replace(tzinfo=tzinfo_value)
        event.add("dtend", end_value)
    event.add("dtstamp", datetime.now(tz=timezone.utc))
    if params.description is not None:
        event.add("description", params.description)
    if params.location is not None:
        event.add("location", params.location)

    calendar.add_component(event)
    _save_calendar(params.path, calendar)
    return _event_info(event)


def update_event(
    path: Path,
    uid: str,
    summary: Optional[str],
    start: Optional[str],
    end: Optional[str],
    all_day: Optional[bool],
    description: Optional[str],
    location: Optional[str],
    tzid: Optional[str] = None,
) -> EventInfo:
    calendar = _load_calendar(path)
    event = _find_event(calendar, uid)
    tzinfo = _ensure_calendar_timezone(calendar, tzid_override=tzid)

    current_info = _event_info(event)
    target_all_day = current_info.all_day if all_day is None else all_day

    start_value = current_info.start
    if start is not None:
        start_value = parse_event_datetime(start, all_day=target_all_day, tz=tzinfo)
    elif target_all_day and isinstance(start_value, datetime):
        start_value = start_value.date()
    elif not target_all_day and isinstance(start_value, date) and not isinstance(start_value, datetime):
        start_value = datetime.combine(start_value, time.min, tzinfo=tzinfo)

    end_value: Optional[date | datetime] = current_info.end
    if end is not None:
        end_value = parse_event_datetime(end, all_day=target_all_day, tz=tzinfo)
        if target_all_day and isinstance(end_value, date) and not isinstance(end_value, datetime):
            validate_start_end(start_value, end_value, all_day=True, end_inclusive=True)
            end_value = end_value + timedelta(days=1)
    else:
        if target_all_day and end_value is None:
            end_value = normalize_event_end(start_value, None, all_day=True, tz=tzinfo)
        elif target_all_day and isinstance(end_value, datetime):
            end_value = end_value.date()
        elif not target_all_day and isinstance(end_value, date) and not isinstance(end_value, datetime):
            end_value = datetime.combine(end_value, time.min, tzinfo=tzinfo)

    if not target_all_day:
        if isinstance(start_value, datetime) and start_value.tzinfo is None:
            start_value = start_value.replace(tzinfo=tzinfo)
        if isinstance(end_value, datetime) and end_value.tzinfo is None:
            end_value = end_value.replace(tzinfo=tzinfo)

    if target_all_day and end is None and end_value is not None:
        start_date = start_value if isinstance(start_value, date) and not isinstance(start_value, datetime) else start_value.date()
        end_date = end_value if isinstance(end_value, date) and not isinstance(end_value, datetime) else end_value.date()
        if end_date <= start_date:
            end_value = start_date + timedelta(days=1)

    end_value = normalize_event_end(start_value, end_value, all_day=target_all_day, tz=tzinfo)
    validate_start_end(start_value, end_value, all_day=target_all_day)

    if summary is not None:
        event["summary"] = summary
    if "dtstart" in event:
        del event["dtstart"]
    event.add("dtstart", start_value)
    if end_value is None:
        if "dtend" in event:
            del event["dtend"]
    else:
        if "dtend" in event:
            del event["dtend"]
        event.add("dtend", end_value)
    if "dtstamp" in event:
        del event["dtstamp"]
    event.add("dtstamp", datetime.now(tz=timezone.utc))
    if description is not None:
        event["description"] = description
    if location is not None:
        event["location"] = location

    _save_calendar(path, calendar)
    return _event_info(event)


def calendar_timezone_for_path(path: Optional[Path], tzid: Optional[str] = None) -> tzinfo:
    if tzid:
        return resolve_timezone(tzid)[0]
    resolved = resolve_calendar_path(path)
    if not resolved.exists():
        return calendar_timezone()[0]
    calendar = _load_calendar(resolved)
    return _calendar_timezone_for_parse(calendar)


def delete_event(path: Path, uid: str) -> EventInfo:
    calendar = _load_calendar(path)
    event = _find_event(calendar, uid)
    info = _event_info(event)
    calendar.subcomponents.remove(event)
    _save_calendar(path, calendar)
    return info
