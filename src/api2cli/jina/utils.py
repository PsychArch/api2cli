"""Utility helpers for Jina CLI."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Mapping

from .config import load_config


@dataclass(frozen=True)
class GitHubUrlResult:
    is_github: bool
    converted_url: str
    original_url: str
    should_bypass_jina: bool


def get_jina_api_key() -> str | None:
    return load_config().api_key


def create_headers(base_headers: Mapping[str, str] | None = None) -> dict[str, str]:
    headers = dict(base_headers or {})
    api_key = get_jina_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def handle_github_url(url: str) -> GitHubUrlResult:
    is_github = "github.com" in url and "/blob/" in url

    if is_github:
        match = re.search(r"github\.com/([^/]+)/([^/]+)/blob/([^/]+)/?(.*)", url)
        if match:
            owner, repo, ref, path = match.groups()
            is_commit_hash = re.fullmatch(r"[a-f0-9]{40}", ref, flags=re.IGNORECASE) is not None
            if is_commit_hash:
                converted_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
            else:
                converted_url = f"https://raw.githubusercontent.com/{owner}/{repo}/refs/heads/{ref}/{path}"
        else:
            converted_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

        return GitHubUrlResult(
            is_github=True,
            converted_url=converted_url,
            original_url=url,
            should_bypass_jina=True,
        )

    return GitHubUrlResult(
        is_github=False,
        converted_url=url,
        original_url=url,
        should_bypass_jina=False,
    )


def build_jina_headers(is_github: bool) -> dict[str, str]:
    base_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Md-Link-Style": "discarded",
        "X-With-Links-Summary": "all",
        "X-Retain-Images": "none",
    }

    if is_github:
        return {
            **base_headers,
            "X-Engine": "direct",
            "X-Return-Format": "text",
            "X-Timeout": "10",
        }

    return base_headers


def ttl_from_headers(headers: Mapping[str, str]) -> int | None:
    cache_control = headers.get("Cache-Control") or headers.get("cache-control")
    if cache_control:
        lowered = cache_control.lower()
        if "no-store" in lowered or "no-cache" in lowered:
            return 0
        match = re.search(r"max-age=(\d+)", lowered)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None

    expires = headers.get("Expires") or headers.get("expires")
    if expires:
        try:
            expires_dt = parsedate_to_datetime(expires)
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = (expires_dt - now).total_seconds()
            return max(0, int(delta))
        except (TypeError, ValueError):
            return None

    return None
