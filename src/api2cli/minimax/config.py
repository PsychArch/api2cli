"""Configuration loader for Minimax CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .errors import MinimaxConfigError
from .constants import API_BASE_URL, DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class MinimaxConfig:
    api_key: str
    api_host: str
    timeout_seconds: float
    retry_attempts: int
    retry_delay_seconds: float


def load_config() -> MinimaxConfig:
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        raise MinimaxConfigError("Required environment variable MINIMAX_API_KEY is not set")

    api_host = os.getenv("MINIMAX_API_HOST", API_BASE_URL)
    timeout = float(os.getenv("MINIMAX_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS)))
    retry_attempts = int(os.getenv("MINIMAX_RETRY_ATTEMPTS", "3"))
    retry_delay = float(os.getenv("MINIMAX_RETRY_DELAY", "1"))

    return MinimaxConfig(
        api_key=api_key,
        api_host=api_host,
        timeout_seconds=timeout,
        retry_attempts=retry_attempts,
        retry_delay_seconds=retry_delay,
    )
