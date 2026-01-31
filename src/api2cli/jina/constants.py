"""Constants for Jina AI CLI."""

from __future__ import annotations

API_READER_URL = "https://r.jina.ai/"
API_SEARCH_URL = "https://s.jina.ai/"
API_SEARCH_VIP_URL = "https://svip.jina.ai/"

DEFAULTS = {
    "TOKENS_PER_PAGE": 15000,
    "CACHE_SIZE": 50,
    "CACHE_TTL_SECONDS": 3600,
    "SEARCH_COUNT": 5,
    "SEARCH_ENDPOINT": "standard",
}

SEARCH_ENDPOINTS = {"standard", "vip"}
