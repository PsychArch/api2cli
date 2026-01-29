"""Image generation for Minimax API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .client import MinimaxClient
from .constants import DEFAULTS, ENDPOINTS
from .errors import MinimaxError
from .file_utils import convert_to_base64, download_file, generate_unique_filename, save_base64_image
from .validators import ImageParams


@dataclass(frozen=True)
class ImageResult:
    files: list[Path]
    count: int
    model: str
    prompt: str
    warnings: list[str] | None = None


def _build_payload(params: ImageParams, timeout: float) -> dict[str, Any]:
    model = "image-01-live" if params.style_type else "image-01"
    payload: dict[str, Any] = {
        "model": model,
        "prompt": params.prompt,
        "n": 1,
        "prompt_optimizer": True,
        "response_format": "url",
    }

    if params.custom_size:
        width, height = params.custom_size
        payload["width"] = width
        payload["height"] = height
    else:
        payload["aspect_ratio"] = params.aspect_ratio or DEFAULTS["IMAGE"]["aspect_ratio"]

    if params.seed is not None:
        payload["seed"] = params.seed

    if model == "image-01":
        if params.subject_reference:
            reference = params.subject_reference
            if reference.startswith("http://") or reference.startswith("https://"):
                image_file = reference
            else:
                image_file = convert_to_base64(reference, timeout)
            payload["subject_reference"] = [{
                "type": "character",
                "image_file": image_file,
            }]
    else:
        payload["style"] = {
            "style_type": params.style_type,
            "style_weight": params.style_weight or DEFAULTS["IMAGE"]["style_weight"],
        }

    return payload


def generate_image(client: MinimaxClient, params: ImageParams) -> ImageResult:
    payload = _build_payload(params, client.timeout)
    response = client.post(ENDPOINTS["IMAGE_GENERATION"], payload)

    data = response.get("data") or {}
    image_urls = data.get("image_urls") or []
    image_base64 = data.get("image_base64") or []

    if not image_urls and not image_base64:
        raise MinimaxError("No images generated in API response")

    saved_files: list[Path] = []
    errors: list[str] = []
    image_sources = image_urls if image_urls else image_base64
    total = len(image_sources)

    for index, source in enumerate(image_sources):
        filename = generate_unique_filename(params.output_file, index, total)
        try:
            if image_base64 and not image_urls:
                save_base64_image(source, filename)
            else:
                download_file(source, filename, timeout=client.timeout)
            saved_files.append(filename)
        except MinimaxError as exc:
            errors.append(f"Image {index + 1}: {exc}")

    if not saved_files:
        raise MinimaxError(f"Failed to save any images: {'; '.join(errors)}")

    model_used = "image-01-live" if params.style_type else "image-01"

    return ImageResult(
        files=saved_files,
        count=len(saved_files),
        model=model_used,
        prompt=params.prompt,
        warnings=errors or None,
    )
