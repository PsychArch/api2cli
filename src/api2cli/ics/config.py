"""Configuration helpers for iCalendar support."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .constants import DEFAULT_CALENDAR_FILENAME


def default_calendar_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base_dir = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return base_dir / "api2cli" / DEFAULT_CALENDAR_FILENAME


def resolve_calendar_path(path: Optional[Path]) -> Path:
    resolved = (path or default_calendar_path()).expanduser()
    return resolved.resolve()


def local_timezone():
    return datetime.now().astimezone().tzinfo
