from __future__ import annotations

from pathlib import Path
from typing import Any

from setandnotes.services.media_probe import FFProbeMediaProbe, MediaProbe

SUPPORTED_MEDIA_EXTENSIONS = {
    ".aif",
    ".aiff",
    ".flac",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".wav",
    ".mxf",
}


def is_supported_media_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_MEDIA_EXTENSIONS


def scan_media_folder(folder: Path | str, probe: MediaProbe | None = None) -> list[dict[str, Any]]:
    root = Path(folder)
    active_probe = probe or FFProbeMediaProbe()
    results: list[dict[str, Any]] = []

    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if not is_supported_media_file(path):
            continue
        results.append(active_probe.probe(path))

    return results
