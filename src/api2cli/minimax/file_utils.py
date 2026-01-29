"""File handling utilities for Minimax CLI."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Iterable

import requests

from .errors import MinimaxError


def ensure_directory_exists(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise MinimaxError(f"Failed to create directory: {exc}") from exc


def write_file(path: Path, data: bytes) -> None:
    try:
        ensure_directory_exists(path)
        path.write_bytes(data)
    except OSError as exc:
        raise MinimaxError(f"Failed to write file {path}: {exc}") from exc


def download_file(url: str, output_path: Path, timeout: float) -> None:
    try:
        ensure_directory_exists(output_path)
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        output_path.write_bytes(response.content)
    except requests.RequestException as exc:
        raise MinimaxError(f"Failed to download file from {url}: {exc}") from exc
    except OSError as exc:
        raise MinimaxError(f"Failed to write file {output_path}: {exc}") from exc


def convert_to_base64(value: str, timeout: float) -> str:
    if value.startswith("http://") or value.startswith("https://"):
        try:
            response = requests.get(value, timeout=timeout)
            response.raise_for_status()
            data = response.content
        except requests.RequestException as exc:
            raise MinimaxError(f"Failed to download subject reference: {exc}") from exc
    else:
        path = Path(value)
        if not path.is_file():
            raise MinimaxError(f"Subject reference path does not exist: {value}")
        data = path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def generate_unique_filename(base_path: Path, index: int, total: int) -> Path:
    if total <= 1:
        return base_path
    name = base_path.stem
    ext = base_path.suffix
    return base_path.with_name(f"{name}_{index + 1:02d}{ext}")


def save_base64_image(base64_data: str, output_path: Path) -> None:
    try:
        ensure_directory_exists(output_path)
        cleaned = base64_data.split("base64,", 1)[-1]
        data = base64.b64decode(cleaned)
        output_path.write_bytes(data)
    except (OSError, ValueError) as exc:
        raise MinimaxError(f"Failed to save base64 image: {exc}") from exc


def ensure_absolute(path: Path) -> Path:
    return path.expanduser().resolve()


def ensure_extension(path: Path, allowed: Iterable[str], default_ext: str) -> Path:
    if path.suffix:
        return path
    if default_ext not in allowed:
        return path.with_suffix(default_ext)
    return path.with_suffix(default_ext)
