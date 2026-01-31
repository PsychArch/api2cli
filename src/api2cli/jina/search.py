"""Web search integration for Jina AI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

from .config import load_config
from .constants import API_SEARCH_URL, API_SEARCH_VIP_URL
from .errors import JinaAPIError, JinaConfigError, JinaNetworkError, JinaTimeoutError
from .utils import create_headers
from .validators import SearchParams


@dataclass(frozen=True)
class SearchResult:
    text: str


def search_web(params: SearchParams) -> SearchResult:
    api_key = load_config().api_key
    if not api_key:
        raise JinaConfigError("Required environment variable JINA_API_KEY is not set for search")

    base_headers = {
        "Accept": "application/json",
        "X-Respond-With": "no-content",
    }
    if params.site_filter:
        base_headers["X-Site"] = params.site_filter

    headers = create_headers(base_headers)
    endpoint = API_SEARCH_VIP_URL if params.endpoint == "vip" else API_SEARCH_URL
    encoded_query = requests.utils.quote(params.query)

    try:
        response = requests.get(f"{endpoint}?q={encoded_query}", headers=headers)
    except requests.Timeout as exc:
        raise JinaTimeoutError("Request timeout") from exc
    except requests.RequestException as exc:
        raise JinaNetworkError("Network connection failed", exc) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise JinaAPIError("Invalid JSON response from Jina Search API", response=response.text) from exc

    if params.endpoint == "vip":
        _raise_for_vip_error(response, data)
        results = data.get("results") or []
        text = _format_vip_results(results, params.count)
        return SearchResult(text=text)

    _raise_for_standard_error(response, data)
    results = data.get("data") or []
    text = _format_standard_results(results, params.count)
    return SearchResult(text=text)


def _raise_for_standard_error(response: requests.Response, data: dict) -> None:
    if response.ok and data.get("code") == 200:
        return
    message = data.get("message") or f"Jina Search API error ({response.status_code})"
    raise JinaAPIError(message, status_code=response.status_code, response=data)


def _raise_for_vip_error(response: requests.Response, data: dict) -> None:
    if response.ok:
        return
    message = data.get("message") or data.get("error") or f"Jina VIP Search API error ({response.status_code})"
    raise JinaAPIError(message, status_code=response.status_code, response=data)


def _format_standard_results(results: list[dict], count: int) -> str:
    limited = results[:count]
    chunks: list[str] = []
    for index, result in enumerate(limited, start=1):
        title = result.get("title") or ""
        url = result.get("url") or ""
        description = result.get("description")
        date = result.get("date")
        text = f"[{index}] Title: {title}\n"
        text += f"[{index}] URL Source: {url}\n"
        if description:
            text += f"[{index}] Description: {description}\n"
        if date:
            text += f"[{index}] Date: {date}\n"
        chunks.append(text)
    return "\n".join(chunks)


def _format_vip_results(results: list[dict], count: int) -> str:
    limited = results[:count]
    chunks: list[str] = []
    for index, result in enumerate(limited, start=1):
        title = result.get("title") or ""
        url = result.get("url") or ""
        description = result.get("snippet")
        date = result.get("date")
        text = f"[{index}] Title: {title}\n"
        text += f"[{index}] URL Source: {url}\n"
        if description:
            text += f"[{index}] Description: {description}\n"
        if date:
            text += f"[{index}] Date: {date}\n"
        chunks.append(text)
    return "\n".join(chunks)
