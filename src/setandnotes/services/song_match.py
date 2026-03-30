from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from setandnotes.models.library import Library
from setandnotes.models.song import Song, _format_imported_long_name
from setandnotes.models.version import SongVersion
from setandnotes.services.file_classify import ClassifiedMediaFile


@dataclass(frozen=True, slots=True)
class SongImportGroup:
    normalized_name: str
    main_audio_path: str | None = None
    tc_audio_path: str | None = None
    warnings: tuple[str, ...] = ()


def _group_imported_files(files: Iterable[ClassifiedMediaFile]) -> list[SongImportGroup]:
    grouped: dict[str, dict[str, list[ClassifiedMediaFile]]] = defaultdict(lambda: {"main": [], "tc": [], "ambiguous": [], "unknown": []})

    for file in files:
        grouped[file.normalized_name][file.role].append(file)

    groups: list[SongImportGroup] = []
    for normalized_name in sorted(grouped):
        roles = grouped[normalized_name]
        warnings: list[str] = []

        if roles["ambiguous"]:
            warnings.append(
                "ambiguous media classification: "
                + ", ".join(file.source_name for file in roles["ambiguous"])
            )

        if len(roles["main"]) > 1:
            warnings.append("multiple main audio candidates found")
        if len(roles["tc"]) > 1:
            warnings.append("multiple tc audio candidates found")

        main_path = roles["main"][0].source_name if roles["main"] else None
        tc_path = roles["tc"][0].source_name if roles["tc"] else None

        if main_path is None:
            warnings.append("missing main audio")
        if tc_path is None:
            warnings.append("missing tc audio")

        groups.append(
            SongImportGroup(
                normalized_name=normalized_name,
                main_audio_path=main_path,
                tc_audio_path=tc_path,
                warnings=tuple(warnings),
            )
        )

    return groups


def _allocate_song_id(library: Library, normalized_name: str) -> str:
    existing_ids = {song.song_id for song in library.songs}
    if normalized_name not in existing_ids:
        return normalized_name

    suffix = 2
    while f"{normalized_name}_{suffix}" in existing_ids:
        suffix += 1
    return f"{normalized_name}_{suffix}"


def _find_song_by_normalized_name(library: Library, normalized_name: str) -> Song | None:
    for song in library.songs:
        if song.normalized_name == normalized_name:
            return song
    return None


def match_imported_files(
    library: Library,
    files: Iterable[ClassifiedMediaFile],
    *,
    source_folder: str | Path,
    version_label: str,
    source_type: str,
) -> Library:
    for group in _group_imported_files(files):
        song = _find_song_by_normalized_name(library, group.normalized_name)
        if song is None:
            song = Song(
                song_id=_allocate_song_id(library, group.normalized_name),
                long_name=_format_imported_long_name(group.normalized_name),
                normalized_name=group.normalized_name,
            )
            library.add_song(song)

        version = SongVersion(
            version_id=version_label,
            song_id=song.song_id,
            label=version_label,
            source_folder=str(source_folder),
            source_type=source_type,
            main_audio_path=group.main_audio_path,
            tc_audio_path=group.tc_audio_path,
            status="warning" if group.warnings else "ready",
            warnings=list(group.warnings),
        )
        song.attach_version(version)

    return library
