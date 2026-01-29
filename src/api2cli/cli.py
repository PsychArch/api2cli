"""CLI entry point for api2cli."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from api2cli import __version__
from api2cli.minimax import (
    MinimaxClient,
    format_error_for_user,
    generate_image,
    generate_speech,
)
from api2cli.minimax.constants import DEFAULTS, IMAGE_CONSTRAINTS
from api2cli.minimax.validators import (
    parse_custom_size,
    validate_image_params,
    validate_tts_params,
)

app = typer.Typer()
minimax_app = typer.Typer(help="Minimax API tools")
app.add_typer(minimax_app, name="minimax")


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        typer.echo(f"api2cli version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    )
):
    """Convert APIs to CLI tools."""
    pass


@minimax_app.command("image")
def minimax_image(
    prompt: str = typer.Option(..., "--prompt", "-p", help="Image generation prompt."),
    output_file: str = typer.Option(..., "--output-file", "-o", help="Output image file path."),
    aspect_ratio: Optional[str] = typer.Option(
        DEFAULTS["IMAGE"]["aspect_ratio"],
        "--aspect-ratio",
        help=f"Aspect ratio. Options: {', '.join(IMAGE_CONSTRAINTS['ASPECT_RATIOS'])}.",
    ),
    custom_size: Optional[str] = typer.Option(
        None,
        "--custom-size",
        help="Custom size as WIDTHxHEIGHT (512-2048, multiples of 8).",
    ),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed for reproducible results."),
    subject_reference: Optional[str] = typer.Option(
        None,
        "--subject-reference",
        help="File path or URL for portrait reference (image-01 only).",
    ),
    style_type: Optional[str] = typer.Option(
        None,
        "--style-type",
        help="Style type (image-01-live only).",
    ),
    style_weight: Optional[float] = typer.Option(
        None,
        "--style-weight",
        help="Style weight (0.01-1.0).",
    ),
    api_host: Optional[str] = typer.Option(
        None,
        "--api-host",
        help="Override MINIMAX_API_HOST for this request.",
    ),
    timeout: Optional[float] = typer.Option(
        None,
        "--timeout",
        help="Override MINIMAX_TIMEOUT for this request (seconds).",
    ),
):
    """Generate an image with Minimax."""
    try:
        parsed_custom_size = parse_custom_size(custom_size)
        params = validate_image_params(
            prompt=prompt,
            output_file=Path(output_file),
            aspect_ratio=aspect_ratio,
            custom_size=parsed_custom_size,
            seed=seed,
            subject_reference=subject_reference,
            style_type=style_type,
            style_weight=style_weight,
        )
        client = MinimaxClient(base_url=api_host, timeout=timeout)
        result = generate_image(client, params)
    except Exception as exc:
        typer.secho(format_error_for_user(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo(f"✅ Generated {result.count} image(s) using {result.model}")
    for path in result.files:
        typer.echo(str(path))
    if result.warnings:
        typer.echo("Warnings:")
        for warning in result.warnings:
            typer.echo(f"- {warning}")


@minimax_app.command("tts")
def minimax_tts(
    text: str = typer.Option(..., "--text", help="Text to convert to speech."),
    output_file: str = typer.Option(..., "--output-file", "-o", help="Output audio file path."),
    high_quality: bool = typer.Option(
        False,
        "--high-quality",
        help="Use high-quality model (speech-2.8-hd).",
    ),
    voice_id: Optional[str] = typer.Option(
        None,
        "--voice-id",
        help="Voice ID for speech generation.",
    ),
    speed: float = typer.Option(DEFAULTS["TTS"]["speed"], "--speed", help="Speech speed multiplier."),
    volume: float = typer.Option(DEFAULTS["TTS"]["volume"], "--volume", help="Audio volume multiplier."),
    pitch: float = typer.Option(DEFAULTS["TTS"]["pitch"], "--pitch", help="Pitch adjustment (semitones)."),
    emotion: str = typer.Option(DEFAULTS["TTS"]["emotion"], "--emotion", help="Emotion tone."),
    audio_format: str = typer.Option(DEFAULTS["TTS"]["format"], "--format", help="Audio format."),
    sample_rate: int = typer.Option(DEFAULTS["TTS"]["sample_rate"], "--sample-rate", help="Sample rate (Hz)."),
    bitrate: int = typer.Option(DEFAULTS["TTS"]["bitrate"], "--bitrate", help="Bitrate (bps)."),
    language_boost: Optional[str] = typer.Option(
        "auto",
        "--language-boost",
        help="Optional language boost (e.g. English, Chinese,Yue, auto).",
    ),
    intensity: Optional[int] = typer.Option(
        None,
        "--intensity",
        help="Voice intensity adjustment (-100 to 100).",
    ),
    timbre: Optional[int] = typer.Option(
        None,
        "--timbre",
        help="Voice timbre adjustment (-100 to 100).",
    ),
    sound_effects: Optional[str] = typer.Option(
        None,
        "--sound-effects",
        help="Sound effects (spacious_echo, auditorium_echo, lofi_telephone, robotic).",
    ),
    api_host: Optional[str] = typer.Option(
        None,
        "--api-host",
        help="Override MINIMAX_API_HOST for this request.",
    ),
    timeout: Optional[float] = typer.Option(
        None,
        "--timeout",
        help="Override MINIMAX_TIMEOUT for this request (seconds).",
    ),
):
    """Generate speech with Minimax."""
    try:
        params = validate_tts_params(
            text=text,
            output_file=Path(output_file),
            high_quality=high_quality,
            voice_id=voice_id,
            speed=speed,
            volume=volume,
            pitch=pitch,
            emotion=emotion,
            audio_format=audio_format,
            sample_rate=sample_rate,
            bitrate=bitrate,
            language_boost=language_boost,
            intensity=intensity,
            timbre=timbre,
            sound_effects=sound_effects,
        )
        client = MinimaxClient(base_url=api_host, timeout=timeout)
        result = generate_speech(client, params)
    except Exception as exc:
        typer.secho(format_error_for_user(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo(f"✅ Generated speech using {result.model}")
    typer.echo(str(result.audio_file))
    if result.duration is not None:
        typer.echo(f"Duration: {result.duration}")


def cli():
    """Entry point for the CLI."""
    app()
