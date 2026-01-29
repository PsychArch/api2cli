"""Validation helpers for Minimax CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .constants import DEFAULTS, IMAGE_CONSTRAINTS, TTS_CONSTRAINTS, VOICE_IDS
from .errors import MinimaxValidationError
from .file_utils import ensure_absolute


@dataclass(frozen=True)
class ImageParams:
    prompt: str
    output_file: Path
    aspect_ratio: str
    custom_size: Optional[tuple[int, int]]
    seed: Optional[int]
    subject_reference: Optional[str]
    style_type: Optional[str]
    style_weight: Optional[float]


@dataclass(frozen=True)
class TTSParams:
    text: str
    output_file: Path
    high_quality: bool
    voice_id: str
    speed: float
    volume: float
    pitch: int
    emotion: str
    audio_format: str
    sample_rate: int
    bitrate: int
    language_boost: Optional[str]
    intensity: Optional[int]
    timbre: Optional[int]
    sound_effects: Optional[str]


def parse_custom_size(value: Optional[str]) -> Optional[tuple[int, int]]:
    if value is None:
        return None
    if "x" not in value:
        raise MinimaxValidationError("custom-size must be formatted as WIDTHxHEIGHT", field="custom_size", value=value)
    width_str, height_str = value.lower().split("x", 1)
    try:
        width = int(width_str)
        height = int(height_str)
    except ValueError as exc:
        raise MinimaxValidationError("custom-size must contain integers", field="custom_size", value=value) from exc
    return width, height


def validate_image_params(
    prompt: str,
    output_file: Path,
    aspect_ratio: Optional[str],
    custom_size: Optional[tuple[int, int]],
    seed: Optional[int],
    subject_reference: Optional[str],
    style_type: Optional[str],
    style_weight: Optional[float],
) -> ImageParams:
    if not prompt:
        raise MinimaxValidationError("Prompt is required", field="prompt")
    if len(prompt) > IMAGE_CONSTRAINTS["PROMPT_MAX_LENGTH"]:
        raise MinimaxValidationError(
            f"Prompt must not exceed {IMAGE_CONSTRAINTS['PROMPT_MAX_LENGTH']} characters",
            field="prompt",
            value=prompt,
        )

    if not output_file:
        raise MinimaxValidationError("Output file is required", field="output_file")

    aspect_ratio_value = aspect_ratio or DEFAULTS["IMAGE"]["aspect_ratio"]
    if aspect_ratio_value not in IMAGE_CONSTRAINTS["ASPECT_RATIOS"]:
        raise MinimaxValidationError(
            f"Invalid aspect ratio. Allowed: {', '.join(IMAGE_CONSTRAINTS['ASPECT_RATIOS'])}",
            field="aspect_ratio",
            value=aspect_ratio_value,
        )

    if custom_size is not None:
        width, height = custom_size
        if width < IMAGE_CONSTRAINTS["MIN_DIMENSION"] or width > IMAGE_CONSTRAINTS["MAX_DIMENSION"]:
            raise MinimaxValidationError("Custom width out of range", field="custom_size", value=custom_size)
        if height < IMAGE_CONSTRAINTS["MIN_DIMENSION"] or height > IMAGE_CONSTRAINTS["MAX_DIMENSION"]:
            raise MinimaxValidationError("Custom height out of range", field="custom_size", value=custom_size)
        step = IMAGE_CONSTRAINTS["DIMENSION_STEP"]
        if width % step != 0 or height % step != 0:
            raise MinimaxValidationError(
                f"Custom size must be multiples of {step}",
                field="custom_size",
                value=custom_size,
            )

    if seed is not None and seed <= 0:
        raise MinimaxValidationError("Seed must be a positive integer", field="seed", value=seed)

    if style_type and custom_size:
        raise MinimaxValidationError(
            "style-type cannot be combined with custom-size",
            field="style_type",
        )
    if style_type and subject_reference:
        raise MinimaxValidationError(
            "style-type cannot be combined with subject-reference",
            field="style_type",
        )

    if style_type and style_type not in IMAGE_CONSTRAINTS["STYLE_TYPES"]:
        raise MinimaxValidationError(
            f"Invalid style-type. Allowed: {', '.join(IMAGE_CONSTRAINTS['STYLE_TYPES'])}",
            field="style_type",
            value=style_type,
        )

    if style_weight is not None:
        if style_weight < IMAGE_CONSTRAINTS["STYLE_WEIGHT_MIN"] or style_weight > IMAGE_CONSTRAINTS["STYLE_WEIGHT_MAX"]:
            raise MinimaxValidationError(
                f"style-weight must be between {IMAGE_CONSTRAINTS['STYLE_WEIGHT_MIN']} and {IMAGE_CONSTRAINTS['STYLE_WEIGHT_MAX']}",
                field="style_weight",
                value=style_weight,
            )

    normalized_output = ensure_absolute(output_file)

    return ImageParams(
        prompt=prompt,
        output_file=normalized_output,
        aspect_ratio=aspect_ratio_value,
        custom_size=custom_size,
        seed=seed,
        subject_reference=subject_reference,
        style_type=style_type,
        style_weight=style_weight,
    )


def validate_tts_params(
    text: str,
    output_file: Path,
    high_quality: bool,
    voice_id: Optional[str],
    speed: float,
    volume: float,
    pitch: float,
    emotion: str,
    audio_format: str,
    sample_rate: int,
    bitrate: int,
    language_boost: Optional[str],
    intensity: Optional[int],
    timbre: Optional[int],
    sound_effects: Optional[str],
) -> TTSParams:
    if not text:
        raise MinimaxValidationError("Text is required", field="text")
    if len(text) > TTS_CONSTRAINTS["TEXT_MAX_LENGTH"]:
        raise MinimaxValidationError(
            f"Text must not exceed {TTS_CONSTRAINTS['TEXT_MAX_LENGTH']} characters",
            field="text",
            value=text,
        )

    if speed < TTS_CONSTRAINTS["SPEED_MIN"] or speed > TTS_CONSTRAINTS["SPEED_MAX"]:
        raise MinimaxValidationError("Speed out of range", field="speed", value=speed)
    if volume < TTS_CONSTRAINTS["VOLUME_MIN"] or volume > TTS_CONSTRAINTS["VOLUME_MAX"]:
        raise MinimaxValidationError("Volume out of range", field="volume", value=volume)
    if pitch < TTS_CONSTRAINTS["PITCH_MIN"] or pitch > TTS_CONSTRAINTS["PITCH_MAX"]:
        raise MinimaxValidationError("Pitch out of range", field="pitch", value=pitch)
    if not float(pitch).is_integer():
        raise MinimaxValidationError("Pitch must be an integer semitone value", field="pitch", value=pitch)

    if emotion not in TTS_CONSTRAINTS["EMOTIONS"]:
        raise MinimaxValidationError(
            f"Invalid emotion. Allowed: {', '.join(TTS_CONSTRAINTS['EMOTIONS'])}",
            field="emotion",
            value=emotion,
        )

    if audio_format not in TTS_CONSTRAINTS["FORMATS"]:
        raise MinimaxValidationError(
            f"Invalid format. Allowed: {', '.join(TTS_CONSTRAINTS['FORMATS'])}",
            field="format",
            value=audio_format,
        )

    if sample_rate not in TTS_CONSTRAINTS["SAMPLE_RATES"]:
        raise MinimaxValidationError(
            f"Invalid sample-rate. Allowed: {', '.join(str(v) for v in TTS_CONSTRAINTS['SAMPLE_RATES'])}",
            field="sample_rate",
            value=sample_rate,
        )

    if bitrate not in TTS_CONSTRAINTS["BITRATES"]:
        raise MinimaxValidationError(
            f"Invalid bitrate. Allowed: {', '.join(str(v) for v in TTS_CONSTRAINTS['BITRATES'])}",
            field="bitrate",
            value=bitrate,
        )

    if intensity is not None:
        if intensity < TTS_CONSTRAINTS["VOICE_MODIFY_INTENSITY_MIN"] or intensity > TTS_CONSTRAINTS["VOICE_MODIFY_INTENSITY_MAX"]:
            raise MinimaxValidationError("Intensity out of range", field="intensity", value=intensity)

    if timbre is not None:
        if timbre < TTS_CONSTRAINTS["VOICE_MODIFY_TIMBRE_MIN"] or timbre > TTS_CONSTRAINTS["VOICE_MODIFY_TIMBRE_MAX"]:
            raise MinimaxValidationError("Timbre out of range", field="timbre", value=timbre)

    if sound_effects is not None and sound_effects not in TTS_CONSTRAINTS["SOUND_EFFECTS"]:
        raise MinimaxValidationError(
            f"Invalid sound-effects. Allowed: {', '.join(TTS_CONSTRAINTS['SOUND_EFFECTS'])}",
            field="sound_effects",
            value=sound_effects,
        )

    voice_id_value = voice_id or DEFAULTS["TTS"]["voice_id"]
    if voice_id_value not in VOICE_IDS:
        raise MinimaxValidationError(
            f"Unknown voice-id. Allowed: {', '.join(VOICE_IDS)}",
            field="voice_id",
            value=voice_id_value,
        )

    normalized_output = ensure_absolute(output_file)

    pitch_value = int(pitch)

    return TTSParams(
        text=text,
        output_file=normalized_output,
        high_quality=high_quality,
        voice_id=voice_id_value,
        speed=speed,
        volume=volume,
        pitch=pitch_value,
        emotion=emotion,
        audio_format=audio_format,
        sample_rate=sample_rate,
        bitrate=bitrate,
        language_boost=language_boost,
        intensity=intensity,
        timbre=timbre,
        sound_effects=sound_effects,
    )
