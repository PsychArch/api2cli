"""Configuration helpers for iCalendar support."""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone, tzinfo
from functools import lru_cache
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .constants import DEFAULT_CALENDAR_FILENAME


def default_calendar_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base_dir = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return base_dir / "api2cli" / DEFAULT_CALENDAR_FILENAME


def resolve_calendar_path(path: Optional[Path]) -> Path:
    resolved = (path or default_calendar_path()).expanduser()
    return resolved.resolve()


def _format_utc_offset(offset: timedelta) -> str:
    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def _tz_name_from_path(path: Path) -> Optional[str]:
    try:
        resolved = path.resolve()
    except OSError:
        return None
    marker = "/zoneinfo/"
    resolved_str = resolved.as_posix()
    if marker in resolved_str:
        return resolved_str.split(marker, 1)[1]
    return None


def _detect_tz_name() -> Optional[str]:
    timezone_file = Path("/etc/timezone")
    if timezone_file.exists():
        try:
            content = timezone_file.read_text(encoding="utf-8").strip()
        except OSError:
            content = ""
        if content:
            return content

    localtime = Path("/etc/localtime")
    if localtime.exists():
        derived = _tz_name_from_path(localtime)
        if derived:
            return derived
    return None


def _is_iana_tzid(value: str) -> bool:
    return value == "UTC" or "/" in value


_UTC_OFFSET_RE = re.compile(r"^UTC([+-])(\\d{2}):?(\\d{2})$")


@lru_cache(maxsize=1)
def calendar_timezone() -> tuple[tzinfo, str]:
    tz_name = _detect_tz_name()
    if tz_name:
        try:
            tzinfo_value = ZoneInfo(tz_name)
            return tzinfo_value, tz_name
        except ZoneInfoNotFoundError:
            pass

    now = datetime.now().astimezone()
    system_tz = now.tzinfo or timezone.utc
    tzid = None
    for attr in ("key", "zone"):
        value = getattr(system_tz, attr, None)
        if value and _is_iana_tzid(value):
            tzid = value
            break
    if tzid:
        return system_tz, tzid

    offset = now.utcoffset() or timedelta()
    tzid = _format_utc_offset(offset)
    return timezone(offset, name=tzid), tzid


def resolve_timezone(tzid: Optional[str]) -> tuple[tzinfo, str]:
    if tzid is None:
        return calendar_timezone()
    tzid = tzid.strip()
    if not tzid:
        return calendar_timezone()
    tzinfo_value = tzinfo_for_tzid(tzid)
    if tzinfo_value is not None:
        return tzinfo_value, tzid
    match = _UTC_OFFSET_RE.match(tzid)
    if match:
        sign, hours, minutes = match.groups()
        offset = timedelta(hours=int(hours), minutes=int(minutes))
        if sign == "-":
            offset = -offset
        return timezone(offset, name=tzid), tzid
    raise ValueError(f"Invalid timezone '{tzid}'")


def tzinfo_for_tzid(tzid: Optional[str]) -> Optional[tzinfo]:
    if not tzid:
        return None
    try:
        return ZoneInfo(tzid)
    except ZoneInfoNotFoundError:
        return None


def local_timezone() -> tzinfo:
    return calendar_timezone()[0]
