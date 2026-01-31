"""Token counting helpers for Jina pagination."""

from __future__ import annotations

from typing import Optional

import tiktoken

_encoder: Optional[tiktoken.Encoding] = None


def get_encoder() -> tiktoken.Encoding:
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("o200k_base")
    return _encoder


def count_tokens(text: str) -> int:
    encoder = get_encoder()
    return len(encoder.encode(text, allowed_special="all"))
