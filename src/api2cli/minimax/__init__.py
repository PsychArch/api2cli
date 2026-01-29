"""Minimax API integration for api2cli."""

from .client import MinimaxClient
from .errors import (
    MinimaxAPIError,
    MinimaxConfigError,
    MinimaxError,
    MinimaxNetworkError,
    MinimaxRateLimitError,
    MinimaxTimeoutError,
    MinimaxValidationError,
    format_error_for_user,
)
from .image import ImageResult, generate_image
from .tts import TTSResult, generate_speech
from .validators import ImageParams, TTSParams

__all__ = [
    "MinimaxClient",
    "MinimaxError",
    "MinimaxAPIError",
    "MinimaxConfigError",
    "MinimaxNetworkError",
    "MinimaxTimeoutError",
    "MinimaxRateLimitError",
    "MinimaxValidationError",
    "format_error_for_user",
    "ImageParams",
    "TTSParams",
    "ImageResult",
    "TTSResult",
    "generate_image",
    "generate_speech",
]
