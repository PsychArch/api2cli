"""Web reader integration for Jina AI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

from .cache import DiskCache, CacheEntry, ensure_cache_directory
from .constants import API_READER_URL
from .errors import JinaAPIError, JinaNetworkError, JinaTimeoutError
from .pagination import get_page, paginate_content
from .tokenizer import count_tokens
from .utils import build_jina_headers, create_headers, handle_github_url, ttl_from_headers
from .validators import ReaderParams


@dataclass(frozen=True)
class ReaderResult:
    text: str
    page: int
    total_pages: int
    tokens: int


def read_page(params: ReaderParams) -> ReaderResult:
    ensure_cache_directory(params.cache_path)
    cache = DiskCache(params.cache_path, params.cache_size)

    try:
        cached = cache.get(params.url)
        if cached:
            return _format_cached_page(cached, params)

        content, ttl_hint = _fetch_content(params.url, params.custom_timeout)
        total_tokens = count_tokens(content)
        ttl_seconds = _resolve_ttl(ttl_hint, params.cache_ttl)
        cache.set(params.url, content, "text", ttl_seconds, total_tokens=total_tokens)

        pages = paginate_content(content, params.tokens_per_page)
        page = get_page(pages, params.page)
        if not page:
            raise JinaAPIError(f"Page {params.page} not found. Total pages: {len(pages)}")

        formatted = _format_page(page.content, params.page, len(pages), page.tokens)
        return ReaderResult(text=formatted, page=params.page, total_pages=len(pages), tokens=page.tokens)
    finally:
        cache.close()


def _format_cached_page(cached: CacheEntry, params: ReaderParams) -> ReaderResult:
    if cached.value_type != "text":
        raise JinaAPIError("Cached entry has unexpected type", response={"value_type": cached.value_type})
    pages = paginate_content(cached.value, params.tokens_per_page)
    page = get_page(pages, params.page)
    if not page:
        raise JinaAPIError(f"Page {params.page} not found. Total pages: {len(pages)}")

    formatted = _format_page(page.content, params.page, len(pages), page.tokens)
    return ReaderResult(text=formatted, page=params.page, total_pages=len(pages), tokens=page.tokens)


def _format_page(content: str, page: int, total_pages: int, tokens: int) -> str:
    pagination_info = f"Page {page} of {total_pages} | {tokens} tokens"
    return f"{pagination_info}\n{'=' * 60}\n\n{content}"


def _fetch_content(url: str, custom_timeout: Optional[float]) -> tuple[str, Optional[int]]:
    github = handle_github_url(url)
    actual_url = github.converted_url

    if github.should_bypass_jina:
        response = _request_raw(actual_url, timeout=custom_timeout)
        content = response.text
        ttl_hint = ttl_from_headers(response.headers)
        return content, ttl_hint

    jina_headers = build_jina_headers(github.is_github)
    if custom_timeout is not None:
        jina_headers["X-Timeout"] = str(custom_timeout)

    headers = create_headers(jina_headers)
    response = _request_json(API_READER_URL, headers, {"url": actual_url}, timeout=custom_timeout)

    ttl_hint = ttl_from_headers(response.headers)
    data = response.json_data
    response_data = data.get("data") or {}
    content = response_data.get("content") or "No content extracted"

    return content, ttl_hint


def _request_raw(url: str, timeout: Optional[float]) -> requests.Response:
    try:
        response = requests.get(url, timeout=timeout)
    except requests.Timeout as exc:
        raise JinaTimeoutError("Request timeout", timeout=timeout) from exc
    except requests.RequestException as exc:
        raise JinaNetworkError("Network connection failed", exc) from exc

    if not response.ok:
        message = response.text.strip() or response.reason
        raise JinaAPIError(f"HTTP error ({response.status_code}): {message}", status_code=response.status_code)

    return response


class _JsonResponse:
    def __init__(self, response: requests.Response, json_data: dict[str, object]) -> None:
        self.response = response
        self.json_data = json_data

    @property
    def headers(self) -> requests.structures.CaseInsensitiveDict:  # type: ignore[override]
        return self.response.headers


def _request_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, str],
    timeout: Optional[float],
) -> _JsonResponse:
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.Timeout as exc:
        raise JinaTimeoutError("Request timeout", timeout=timeout) from exc
    except requests.RequestException as exc:
        raise JinaNetworkError("Network connection failed", exc) from exc

    if not response.ok:
        message = response.text.strip() or response.reason
        raise JinaAPIError(f"Jina Reader API error ({response.status_code}): {message}", status_code=response.status_code)

    try:
        data = response.json()
    except ValueError as exc:
        raise JinaAPIError("Invalid JSON response from Jina Reader API", response=response.text) from exc

    return _JsonResponse(response, data)


def _resolve_ttl(ttl_hint: Optional[int], fallback_ttl: int) -> int:
    if ttl_hint is None:
        return fallback_ttl
    if ttl_hint <= 0:
        return 0
    if fallback_ttl <= 0:
        return ttl_hint
    return min(ttl_hint, fallback_ttl)
