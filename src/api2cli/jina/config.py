"""Configuration loader for Jina CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class JinaConfig:
    api_key: str | None


def load_config() -> JinaConfig:
    return JinaConfig(api_key=os.getenv("JINA_API_KEY"))
