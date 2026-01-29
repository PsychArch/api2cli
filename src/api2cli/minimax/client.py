"""HTTP client for Minimax API."""

from __future__ import annotations

import json
import time
from typing import Any

import requests

from .config import load_config
from .constants import DEFAULT_HEADERS
from .errors import (
    MinimaxAPIError,
    MinimaxError,
    MinimaxNetworkError,
    MinimaxRateLimitError,
    MinimaxTimeoutError,
)


class MinimaxClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        self.config = load_config()
        self.base_url = base_url or self.config.api_host
        self.timeout = timeout or self.config.timeout_seconds
        self.retry_attempts = max(1, self.config.retry_attempts)
        self.retry_delay = max(0.0, self.config.retry_delay_seconds)

    def post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", endpoint, payload)

    def get(self, endpoint: str) -> dict[str, Any]:
        return self._request("GET", endpoint, None)

    def _request(self, method: str, endpoint: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            **DEFAULT_HEADERS,
        }

        last_error: MinimaxError | None = None

        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
            except requests.Timeout as exc:
                last_error = MinimaxTimeoutError("Request timeout", timeout=self.timeout)
                if not self._should_retry(last_error, attempt):
                    raise last_error from exc
                time.sleep(self.retry_delay * attempt)
                continue
            except requests.RequestException as exc:
                last_error = MinimaxNetworkError("Network connection failed", exc)
                if not self._should_retry(last_error, attempt):
                    raise last_error from exc
                time.sleep(self.retry_delay * attempt)
                continue

            if not response.ok:
                status = response.status_code
                message = response.text.strip() or response.reason
                last_error = self._http_error(status, message)
                if not self._should_retry(last_error, attempt):
                    raise last_error
                time.sleep(self.retry_delay * attempt)
                continue

            try:
                data = response.json()
            except json.JSONDecodeError as exc:
                raise MinimaxAPIError("Invalid JSON response from API", response=response.text) from exc

            self._raise_for_api_error(data)
            return data

        if last_error:
            raise last_error
        raise MinimaxError("Unknown error occurred")

    def _raise_for_api_error(self, data: dict[str, Any]) -> None:
        base_resp = data.get("base_resp") or {}
        status_code = base_resp.get("status_code")
        if status_code and status_code != 0:
            status_msg = base_resp.get("status_msg") or "API request failed"
            retry_after = base_resp.get("retry_after")
            if status_code == 1004:
                raise MinimaxAPIError(f"Authentication failed: {status_msg}", status_code, data)
            if status_code == 1013:
                raise MinimaxRateLimitError(f"Rate limit exceeded: {status_msg}", retry_after)
            raise MinimaxAPIError(status_msg, status_code, data)

    def _http_error(self, status_code: int, message: str) -> MinimaxError:
        if status_code == 401:
            return MinimaxAPIError("Unauthorized: Invalid API key", status_code)
        if status_code == 403:
            return MinimaxAPIError("Forbidden: Access denied", status_code)
        if status_code == 404:
            return MinimaxAPIError("Not found: Invalid endpoint", status_code)
        if status_code == 429:
            return MinimaxRateLimitError("Rate limit exceeded")
        if status_code >= 500:
            return MinimaxAPIError("Internal server error", status_code)
        return MinimaxAPIError(message, status_code)

    def _should_retry(self, error: MinimaxError, attempt: int) -> bool:
        if attempt >= self.retry_attempts:
            return False
        if isinstance(error, (MinimaxNetworkError, MinimaxTimeoutError)):
            return True
        if isinstance(error, MinimaxAPIError) and error.status_code and 500 <= error.status_code < 600:
            return True
        return False
