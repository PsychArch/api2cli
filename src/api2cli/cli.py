"""CLI entry point for api2cli."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import typer

from api2cli import __version__
from api2cli.jina import format_error_for_user as format_jina_error
from api2cli.jina import read_page, search_web
from api2cli.jina.cache import default_cache_path
from api2cli.jina.constants import DEFAULTS as JINA_DEFAULTS, SEARCH_ENDPOINTS
from api2cli.jina.validators import validate_reader_params, validate_search_params
from api2cli.ics import (
    add_event,
    calendar_timezone_for_path,
    create_calendar,
    delete_event,
    format_error_for_user as format_ics_error,
    get_event,
    list_events,
    update_event,
    validate_calendar_create_params,
    validate_calendar_path,
    validate_create_params,
    validate_list_params,
    validate_summary,
    validate_timezone,
    validate_uid,
)
from api2cli.minimax import (
    MinimaxClient,
    format_error_for_user as format_minimax_error,
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
jina_app = typer.Typer(help="Jina AI tools")
app.add_typer(jina_app, name="jina")
ics_app = typer.Typer(help="iCalendar (.ics) tools")
app.add_typer(ics_app, name="ics")


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


def _format_event_value(value: date | datetime | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.isoformat()
    return value.isoformat()


def _display_end_for_event(
    start_value: date | datetime,
    end_value: date | datetime | None,
    all_day: bool,
) -> date | datetime | None:
    if end_value is None:
        return None
    if all_day and isinstance(end_value, date) and not isinstance(end_value, datetime):
        start_date = start_value if isinstance(start_value, date) and not isinstance(start_value, datetime) else start_value.date()
        if end_value > start_date:
            return end_value - timedelta(days=1)
    return end_value


def _format_event_compact(info) -> str:
    end_value = _display_end_for_event(info.start, info.end, info.all_day)
    start_str = _format_event_value(info.start)
    end_str = _format_event_value(end_value)
    return f"{info.uid} | {start_str} -> {end_str} | {info.summary}"


def _format_event_detail(info) -> str:
    end_value = _display_end_for_event(info.start, info.end, info.all_day)
    lines = [
        f"UID: {info.uid}",
        f"Summary: {info.summary}",
        f"Start: {_format_event_value(info.start)}",
        f"End: {_format_event_value(end_value)}",
        f"All-day: {'yes' if info.all_day else 'no'}",
    ]
    if info.location is not None:
        lines.append(f"Location: {info.location}")
    if info.description is not None:
        lines.append(f"Description: {info.description}")
    return "\n".join(lines)


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
        typer.secho(format_minimax_error(exc), fg=typer.colors.RED, err=True)
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
        typer.secho(format_minimax_error(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo(f"✅ Generated speech using {result.model}")
    typer.echo(str(result.audio_file))
    if result.duration is not None:
        typer.echo(f"Duration: {result.duration}")


@jina_app.command("reader")
def jina_reader(
    url: str = typer.Option(..., "--url", "-u", help="URL of the webpage to read and extract content from."),
    page: int = typer.Option(1, "--page", help="Page number for paginated content (1-indexed)."),
    tokens_per_page: int = typer.Option(
        JINA_DEFAULTS["TOKENS_PER_PAGE"],
        "--tokens-per-page",
        help="Tokens per page for pagination.",
    ),
    custom_timeout: Optional[float] = typer.Option(
        None,
        "--custom-timeout",
        help="Override timeout in seconds for slow sites.",
    ),
    cache_path: Optional[str] = typer.Option(
        None,
        "--cache-path",
        help="Override the disk cache path (SQLite).",
    ),
    cache_size: int = typer.Option(
        JINA_DEFAULTS["CACHE_SIZE"],
        "--cache-size",
        help="Maximum number of cached URLs to keep.",
    ),
    cache_ttl: int = typer.Option(
        JINA_DEFAULTS["CACHE_TTL_SECONDS"],
        "--cache-ttl",
        help="Cache TTL in seconds (fallback when response has no cache hints).",
    ),
):
    """Read and extract content from a web page using Jina Reader."""
    try:
        resolved_cache_path = Path(cache_path).expanduser() if cache_path else default_cache_path()
        params = validate_reader_params(
            url=url,
            page=page,
            tokens_per_page=tokens_per_page,
            custom_timeout=custom_timeout,
            cache_path=resolved_cache_path,
            cache_size=cache_size,
            cache_ttl=cache_ttl,
        )
        result = read_page(params)
    except Exception as exc:
        typer.secho(format_jina_error(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo(result.text)


@jina_app.command("search")
def jina_search(
    query: str = typer.Option(..., "--query", "-q", help="Search query."),
    count: int = typer.Option(
        JINA_DEFAULTS["SEARCH_COUNT"],
        "--count",
        help="Number of search results to return.",
    ),
    site_filter: Optional[str] = typer.Option(
        None,
        "--site-filter",
        help="Limit search to a specific domain (e.g. github.com).",
    ),
    endpoint: str = typer.Option(
        JINA_DEFAULTS["SEARCH_ENDPOINT"],
        "--endpoint",
        help=f"Search endpoint ({', '.join(sorted(SEARCH_ENDPOINTS))}).",
    ),
):
    """Search the web using Jina Search."""
    try:
        params = validate_search_params(
            query=query,
            count=count,
            site_filter=site_filter,
            endpoint=endpoint,
        )
        result = search_web(params)
    except Exception as exc:
        typer.secho(format_jina_error(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo(result.text)


@ics_app.command("create")
def ics_create(
    file: Optional[str] = typer.Option(
        None,
        "--file",
        "-f",
        help="Calendar file path (defaults to XDG config calendar).",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        help="Calendar display name.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing calendar file.",
    ),
    tz: Optional[str] = typer.Option(
        None,
        "--tz",
        help="Calendar timezone (IANA name like America/Los_Angeles).",
    ),
):
    """Create a new .ics calendar file."""
    try:
        params = validate_calendar_create_params(Path(file) if file else None, name, force)
        tzinfo = validate_timezone(tz)
        tzid = tzinfo[1] if tzinfo else None
        create_calendar(params.path, name=params.name, force=params.force, tzid=tzid)
    except Exception as exc:
        typer.secho(format_ics_error(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo(f"✅ Created calendar at {params.path}")


@ics_app.command("add")
def ics_add(
    summary: str = typer.Option(..., "--summary", "-s", help="Event summary."),
    start: str = typer.Option(..., "--start", help="Event start (ISO 8601)."),
    end: Optional[str] = typer.Option(None, "--end", help="Event end (ISO 8601, optional)."),
    all_day: bool = typer.Option(False, "--all-day", help="Create an all-day event."),
    description: Optional[str] = typer.Option(None, "--description", help="Event description."),
    location: Optional[str] = typer.Option(None, "--location", help="Event location."),
    file: Optional[str] = typer.Option(
        None,
        "--file",
        "-f",
        help="Calendar file path (defaults to XDG config calendar).",
    ),
    tz: Optional[str] = typer.Option(
        None,
        "--tz",
        help="Override calendar timezone (IANA name like America/Los_Angeles).",
    ),
):
    """Add an event to the calendar."""
    try:
        tzinfo_override = validate_timezone(tz)
        tzid = tzinfo_override[1] if tzinfo_override else None
        tzinfo = calendar_timezone_for_path(Path(file) if file else None, tzid=tzid)
        params = validate_create_params(
            Path(file) if file else None,
            summary,
            start,
            end,
            all_day,
            description,
            location,
            tz=tzinfo,
        )
        info = add_event(params, tzid=tzid)
    except Exception as exc:
        typer.secho(format_ics_error(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo(f"✅ Added event {info.uid}")
    typer.echo(_format_event_compact(info))


@ics_app.command("update")
def ics_update(
    uid: str = typer.Option(..., "--uid", help="Event UID."),
    summary: Optional[str] = typer.Option(None, "--summary", "-s", help="Event summary."),
    start: Optional[str] = typer.Option(None, "--start", help="Event start (ISO 8601)."),
    end: Optional[str] = typer.Option(None, "--end", help="Event end (ISO 8601)."),
    all_day: Optional[bool] = typer.Option(
        None,
        "--all-day/--no-all-day",
        help="Toggle all-day status.",
    ),
    description: Optional[str] = typer.Option(None, "--description", help="Event description."),
    location: Optional[str] = typer.Option(None, "--location", help="Event location."),
    file: Optional[str] = typer.Option(
        None,
        "--file",
        "-f",
        help="Calendar file path (defaults to XDG config calendar).",
    ),
    tz: Optional[str] = typer.Option(
        None,
        "--tz",
        help="Override calendar timezone (IANA name like America/Los_Angeles).",
    ),
):
    """Update an event by UID."""
    try:
        calendar_path = validate_calendar_path(Path(file) if file else None)
        validated_uid = validate_uid(uid)
        tzinfo_override = validate_timezone(tz)
        tzid = tzinfo_override[1] if tzinfo_override else None
        if summary is not None:
            validate_summary(summary)
        info = update_event(
            calendar_path,
            validated_uid,
            summary,
            start,
            end,
            all_day,
            description,
            location,
            tzid=tzid,
        )
    except Exception as exc:
        typer.secho(format_ics_error(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo(f"✅ Updated event {info.uid}")
    typer.echo(_format_event_compact(info))


@ics_app.command("delete")
def ics_delete(
    uid: str = typer.Option(..., "--uid", help="Event UID."),
    file: Optional[str] = typer.Option(
        None,
        "--file",
        "-f",
        help="Calendar file path (defaults to XDG config calendar).",
    ),
):
    """Delete an event by UID."""
    try:
        calendar_path = validate_calendar_path(Path(file) if file else None)
        validated_uid = validate_uid(uid)
        info = delete_event(calendar_path, validated_uid)
    except Exception as exc:
        typer.secho(format_ics_error(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo(f"✅ Deleted event {info.uid} | {info.summary}")


@ics_app.command("get")
def ics_get(
    uid: str = typer.Option(..., "--uid", help="Event UID."),
    file: Optional[str] = typer.Option(
        None,
        "--file",
        "-f",
        help="Calendar file path (defaults to XDG config calendar).",
    ),
):
    """Get event details by UID."""
    try:
        calendar_path = validate_calendar_path(Path(file) if file else None)
        validated_uid = validate_uid(uid)
        info = get_event(calendar_path, validated_uid)
    except Exception as exc:
        typer.secho(format_ics_error(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo(_format_event_detail(info))


@ics_app.command("list")
def ics_list(
    file: Optional[str] = typer.Option(
        None,
        "--file",
        "-f",
        help="Calendar file path (defaults to XDG config calendar).",
    ),
    range_from: Optional[str] = typer.Option(
        None,
        "--from",
        help="Filter start range (ISO 8601 date or datetime).",
    ),
    range_to: Optional[str] = typer.Option(
        None,
        "--to",
        help="Filter end range (ISO 8601 date or datetime).",
    ),
    query: Optional[str] = typer.Option(
        None,
        "--query",
        "-q",
        help="Keyword search over summary, description, and location.",
    ),
    tz: Optional[str] = typer.Option(
        None,
        "--tz",
        help="Override calendar timezone (IANA name like America/Los_Angeles).",
    ),
):
    """List events (optionally filtered by date range or keyword)."""
    try:
        tzinfo_override = validate_timezone(tz)
        tzid = tzinfo_override[1] if tzinfo_override else None
        tzinfo = calendar_timezone_for_path(Path(file) if file else None, tzid=tzid)
        params = validate_list_params(Path(file) if file else None, range_from, range_to, query, tz=tzinfo)
        events = list_events(params.path, params.range_start, params.range_end, params.query, tzinfo_override=tzinfo)
    except Exception as exc:
        typer.secho(format_ics_error(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if not events:
        typer.echo("No events found.")
        return

    for info in events:
        typer.echo(_format_event_compact(info))
    typer.echo(f"Total: {len(events)} event(s)")


def cli():
    """Entry point for the CLI."""
    app()
