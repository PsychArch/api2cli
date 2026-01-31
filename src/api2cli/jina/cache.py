"""SQLite-backed disk cache for Jina CLI."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import JinaCacheError


@dataclass(frozen=True)
class CacheEntry:
    key: str
    value: str
    value_type: str
    fetched_at: int
    ttl_seconds: int
    total_tokens: int | None


class DiskCache:
    def __init__(self, path: Path, max_size: int) -> None:
        self.path = path
        self.max_size = max_size
        self._conn = sqlite3.connect(self.path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                value_type TEXT NOT NULL,
                fetched_at INTEGER NOT NULL,
                last_accessed INTEGER NOT NULL,
                ttl_seconds INTEGER NOT NULL,
                total_tokens INTEGER
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except sqlite3.Error as exc:
            raise JinaCacheError("Failed to close cache database", details=str(exc)) from exc

    def get(self, key: str) -> CacheEntry | None:
        now = int(time.time())
        try:
            row = self._conn.execute(
                "SELECT key, value, value_type, fetched_at, ttl_seconds, total_tokens, last_accessed FROM cache WHERE key = ?",
                (key,),
            ).fetchone()
        except sqlite3.Error as exc:
            raise JinaCacheError("Failed to read cache", details=str(exc)) from exc

        if not row:
            return None

        cached_key, value, value_type, fetched_at, ttl_seconds, total_tokens, _last_accessed = row
        if fetched_at + ttl_seconds <= now:
            self._delete(key)
            return None

        try:
            self._conn.execute(
                "UPDATE cache SET last_accessed = ? WHERE key = ?",
                (now, key),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise JinaCacheError("Failed to update cache access time", details=str(exc)) from exc

        return CacheEntry(
            key=cached_key,
            value=value,
            value_type=value_type,
            fetched_at=fetched_at,
            ttl_seconds=ttl_seconds,
            total_tokens=total_tokens,
        )

    def set(self, key: str, value: str, value_type: str, ttl_seconds: int, total_tokens: int | None = None) -> None:
        if ttl_seconds <= 0:
            return
        now = int(time.time())
        try:
            self._conn.execute(
                """
                INSERT INTO cache (key, value, value_type, fetched_at, last_accessed, ttl_seconds, total_tokens)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    value_type = excluded.value_type,
                    fetched_at = excluded.fetched_at,
                    last_accessed = excluded.last_accessed,
                    ttl_seconds = excluded.ttl_seconds,
                    total_tokens = excluded.total_tokens
                """,
                (key, value, value_type, now, now, ttl_seconds, total_tokens),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise JinaCacheError("Failed to write cache", details=str(exc)) from exc

        self._evict_if_needed()

    def _delete(self, key: str) -> None:
        try:
            self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._conn.commit()
        except sqlite3.Error as exc:
            raise JinaCacheError("Failed to delete cache entry", details=str(exc)) from exc

    def _evict_if_needed(self) -> None:
        try:
            self._delete_expired()
            count = self._conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            if count <= self.max_size:
                return
            excess = count - self.max_size
            rows = self._conn.execute(
                "SELECT key FROM cache ORDER BY last_accessed ASC LIMIT ?",
                (excess,),
            ).fetchall()
            for (key,) in rows:
                self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._conn.commit()
        except sqlite3.Error as exc:
            raise JinaCacheError("Failed to evict cache entries", details=str(exc)) from exc

    def _delete_expired(self) -> None:
        now = int(time.time())
        self._conn.execute("DELETE FROM cache WHERE fetched_at + ttl_seconds <= ?", (now,))
        self._conn.commit()


def ensure_cache_directory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def default_cache_path() -> Path:
    base = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "api2cli" / "jina_cache.sqlite3"


def serialize_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=True)
    except (TypeError, ValueError) as exc:
        raise JinaCacheError("Failed to serialize cache value", details=str(exc)) from exc


def deserialize_json(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise JinaCacheError("Failed to parse cached JSON", details=str(exc)) from exc
