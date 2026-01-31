"""Validation helpers for Jina CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .constants import SEARCH_ENDPOINTS
from .errors import JinaValidationError


@dataclass(frozen=True)
class ReaderParams:
    url: str
    page: int
    tokens_per_page: int
    custom_timeout: Optional[float]
    cache_path: Path
    cache_size: int
    cache_ttl: int


@dataclass(frozen=True)
class SearchParams:
    query: str
    count: int
    site_filter: Optional[str]
    endpoint: str


def _validate_url(value: str) -> None:
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        raise JinaValidationError("Invalid URL", field="url", value=value)


def validate_reader_params(
    url: str,
    page: int,
    tokens_per_page: int,
    custom_timeout: Optional[float],
    cache_path: Path,
    cache_size: int,
    cache_ttl: int,
) -> ReaderParams:
    if not url:
        raise JinaValidationError("URL is required", field="url")
    _validate_url(url)

    if page < 1:
        raise JinaValidationError("Page must be >= 1", field="page", value=page)

    if tokens_per_page <= 0:
        raise JinaValidationError("tokens-per-page must be > 0", field="tokens_per_page", value=tokens_per_page)

    if cache_size <= 0:
        raise JinaValidationError("cache-size must be > 0", field="cache_size", value=cache_size)

    if cache_ttl < 0:
        raise JinaValidationError("cache-ttl must be >= 0", field="cache_ttl", value=cache_ttl)

    if custom_timeout is not None and custom_timeout <= 0:
        raise JinaValidationError("custom-timeout must be > 0", field="custom_timeout", value=custom_timeout)

    return ReaderParams(
        url=url,
        page=page,
        tokens_per_page=tokens_per_page,
        custom_timeout=custom_timeout,
        cache_path=cache_path,
        cache_size=cache_size,
        cache_ttl=cache_ttl,
    )


def validate_search_params(
    query: str,
    count: int,
    site_filter: Optional[str],
    endpoint: str,
) -> SearchParams:
    if not query:
        raise JinaValidationError("Query is required", field="query")
    if count <= 0:
        raise JinaValidationError("count must be > 0", field="count", value=count)
    if endpoint not in SEARCH_ENDPOINTS:
        raise JinaValidationError(
            f"Invalid endpoint. Allowed: {', '.join(sorted(SEARCH_ENDPOINTS))}",
            field="endpoint",
            value=endpoint,
        )

    return SearchParams(query=query, count=count, site_filter=site_filter, endpoint=endpoint)
