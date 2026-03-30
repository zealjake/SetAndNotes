from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from setandnotes.models.song import Song


@dataclass(frozen=True, slots=True)
class ValidationResult:
    status: str
    messages: tuple[str, ...]


def _duplicate_long_name_message(song: Song, songs: Sequence[Song]) -> str | None:
    name = song.long_name.strip().casefold()
    if not name:
        return None
    if sum(1 for other in songs if other.long_name.strip().casefold() == name) > 1:
        return f"duplicate long name: {song.long_name}"
    return None


def _duplicate_short_name_message(song: Song, songs: Sequence[Song]) -> str | None:
    short_name = song.short_name.strip().casefold()
    if not short_name:
        return None
    if sum(1 for other in songs if other.short_name.strip().casefold() == short_name) > 1:
        return f"duplicate short name: {song.short_name}"
    return None


def _duplicate_tc_start_message(song: Song, songs: Sequence[Song]) -> str | None:
    try:
        version = song.active_version()
    except ValueError:
        return None

    tc_start = (version.decoded_tc_start or "").strip().casefold()
    if not tc_start:
        return None
    if sum(
        1
        for other in songs
        if other.active_version_id is not None
        and other.active_version().decoded_tc_start
        and other.active_version().decoded_tc_start.strip().casefold() == tc_start
    ) > 1:
        return f"duplicate tc start: {version.decoded_tc_start}"
    return None


def validate_song(song: Song, songs: Sequence[Song] | None = None) -> ValidationResult:
    messages: list[str] = []
    status = "ok"
    project_songs = tuple(songs or (song,))

    if not song.long_name.strip():
        messages.append("missing song long name")
        status = "error"

    if song.bpm is None:
        messages.append("missing bpm")
        if status == "ok":
            status = "warning"

    try:
        version = song.active_version()
    except ValueError:
        messages.append("missing active version")
        return ValidationResult(status="error", messages=tuple(messages))

    if not version.main_audio_path:
        messages.append("missing main audio path")
        status = "error"

    if not version.tc_audio_path:
        messages.append("missing tc audio path")
        status = "error"

    if not version.decoded_tc_start:
        messages.append("missing decoded tc start")
        status = "error"

    if version.status != "ready" and status == "ok":
        status = "warning"

    for warning in version.warnings:
        messages.append(warning)
        if status == "ok":
            status = "warning"

    duplicate_long_name = _duplicate_long_name_message(song, project_songs)
    if duplicate_long_name is not None:
        messages.append(duplicate_long_name)
        status = "error"

    duplicate_short_name = _duplicate_short_name_message(song, project_songs)
    if duplicate_short_name is not None:
        messages.append(duplicate_short_name)
        if status == "ok":
            status = "warning"

    duplicate_tc_start = _duplicate_tc_start_message(song, project_songs)
    if duplicate_tc_start is not None:
        messages.append(duplicate_tc_start)
        status = "error"

    return ValidationResult(status=status, messages=tuple(messages))
