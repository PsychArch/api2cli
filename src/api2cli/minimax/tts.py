"""Text-to-speech generation for Minimax API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .client import MinimaxClient
from .constants import DEFAULTS, ENDPOINTS
from .errors import MinimaxError
from .file_utils import write_file
from .validators import TTSParams


@dataclass(frozen=True)
class TTSResult:
    audio_file: Path
    voice_used: str
    model: str
    duration: float | None
    audio_format: str
    sample_rate: int
    bitrate: int


def _clean_payload(obj: Any) -> Any:
    if not isinstance(obj, dict):
        return obj
    cleaned: dict[str, Any] = {}
    for key, value in obj.items():
        if value is None:
            continue
        if isinstance(value, dict):
            nested = _clean_payload(value)
            if nested:
                cleaned[key] = nested
            continue
        cleaned[key] = value
    return cleaned


def _build_payload(params: TTSParams) -> dict[str, Any]:
    model = "speech-2.8-hd" if params.high_quality else "speech-2.8-turbo"
    payload: dict[str, Any] = {
        "model": model,
        "text": params.text,
        "output_format": "hex",
        "continuous_sound": True,
        "voice_setting": {
            "voice_id": params.voice_id,
            "speed": params.speed,
            "vol": params.volume,
            "pitch": params.pitch,
            "emotion": params.emotion,
        },
        "audio_setting": {
            "sample_rate": params.sample_rate,
            "bitrate": params.bitrate,
            "format": params.audio_format,
            "channel": DEFAULTS["TTS"]["channel"],
        },
    }

    if params.language_boost:
        payload["language_boost"] = params.language_boost

    if params.intensity is not None or params.timbre is not None or params.sound_effects is not None:
        payload["voice_modify"] = {
            "intensity": params.intensity,
            "timbre": params.timbre,
            "sound_effects": params.sound_effects,
        }

    return _clean_payload(payload)


def generate_speech(client: MinimaxClient, params: TTSParams) -> TTSResult:
    payload = _build_payload(params)
    response = client.post(ENDPOINTS["TEXT_TO_SPEECH"], payload)
    data = response.get("data") or {}

    audio_hex = data.get("audio")
    if not audio_hex:
        raise MinimaxError("No audio data received from API")

    try:
        audio_bytes = bytes.fromhex(audio_hex)
    except ValueError as exc:
        raise MinimaxError("Invalid audio payload received") from exc

    write_file(params.output_file, audio_bytes)

    return TTSResult(
        audio_file=params.output_file,
        voice_used=params.voice_id,
        model="speech-2.8-hd" if params.high_quality else "speech-2.8-turbo",
        duration=data.get("duration"),
        audio_format=params.audio_format,
        sample_rate=params.sample_rate,
        bitrate=params.bitrate,
    )
