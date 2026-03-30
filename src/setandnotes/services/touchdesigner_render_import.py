from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from setandnotes.models.library import Library

_RENDER_PATTERN = re.compile(
    r"^(?P<long_name>.+)_(?P<asset_type>Multicam|WideShot1080)_TC(?P<hh>\d{2})_(?P<mm>\d{2})_(?P<ss>\d{2})_(?P<ff>\d{2})$"
)


@dataclass(frozen=True, slots=True)
class RenderedVideoFile:
    long_name: str
    asset_type: str
    tc_start: str
    path: str


def parse_rendered_video_filename(filename: str) -> RenderedVideoFile:
    stem = Path(filename).stem
    match = _RENDER_PATTERN.match(stem)
    if match is None:
        raise ValueError(f"unsupported rendered video filename: {filename}")

    tc_start = "{hh}:{mm}:{ss}:{ff}".format(**match.groupdict())
    return RenderedVideoFile(
        long_name=match.group("long_name"),
        asset_type=match.group("asset_type"),
        tc_start=tc_start,
        path=filename,
    )


def import_rendered_video_folder(
    library: Library,
    render_folder: Path | str,
    *,
    return_warnings: bool = False,
):
    folder = Path(render_folder)
    warnings: list[str] = []

    for path in sorted(folder.glob("*.mov")):
        try:
            parsed = parse_rendered_video_filename(path.name)
        except ValueError:
            continue

        matched_song = next((song for song in library.songs if song.long_name == parsed.long_name), None)
        if matched_song is None:
            warnings.append(f"No matching song for rendered video: {path.name}")
            continue

        try:
            version = matched_song.active_version()
        except ValueError:
            warnings.append(f"No active version for rendered video: {path.name}")
            continue

        version.video_assets[parsed.asset_type] = str(path)

    if return_warnings:
        return library, warnings
    return library
