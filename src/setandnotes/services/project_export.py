from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Callable

from setandnotes.models.song import Song
from setandnotes.services.media_probe import FFProbeMediaProbe
from setandnotes.services.template_rpp import TemplateRpp

_ILLEGAL_FILENAME_CHARS = set('<>:"/\\|?*')
_SONG_PROJECT_ID_PATTERN = re.compile(r"^\s*SETANDNOTES_SONG_PROJECT_ID\s+\{?([0-9a-fA-F-]+)\}?\s*$", re.MULTILINE)


def _sanitize_filename(value: str) -> str:
    sanitized = "".join("_" if character in _ILLEGAL_FILENAME_CHARS else character for character in value)
    sanitized = re.sub(r"[\x00-\x1f]", "_", sanitized).strip()
    return sanitized or "project"


def _song_workspace_dir(output_root: Path, song: Song) -> Path:
    return output_root / _sanitize_filename(song.long_name)


def _song_project_path(song_dir: Path, song: Song) -> Path:
    return song_dir / f"{_sanitize_filename(song.long_name)}.rpp"


def _clear_directory_contents(directory: Path) -> None:
    if not directory.exists():
        return

    for entry in directory.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def _copy_active_media_files(song_dir: Path, version) -> tuple[Path, Path, dict[str, Path]]:
    media_dir = song_dir / "Media"
    media_dir.mkdir(parents=True, exist_ok=True)
    _clear_directory_contents(media_dir)

    main_source = Path(version.main_audio_path)
    tc_source = Path(version.tc_audio_path)
    main_destination = media_dir / main_source.name
    tc_destination = media_dir / tc_source.name
    shutil.copy2(main_source, main_destination)
    shutil.copy2(tc_source, tc_destination)
    copied_video_assets: dict[str, Path] = {}
    for asset_type, asset_path in version.video_assets.items():
        source_path = Path(asset_path)
        destination_path = media_dir / source_path.name
        shutil.copy2(source_path, destination_path)
        copied_video_assets[asset_type] = destination_path
    return main_destination, tc_destination, copied_video_assets


def _timecode_to_seconds(value: str, fps: float = 25.0) -> float:
    value = value.strip()
    if not value:
        raise ValueError("empty timecode")

    try:
        return float(value)
    except ValueError:
        pass

    parts = value.split(":")
    if len(parts) != 4:
        raise ValueError(f"unsupported timecode format: {value}")

    hours, minutes, seconds, frames = (int(part) for part in parts)
    return ((hours * 60 + minutes) * 60 + seconds) + frames / fps


def _fps_to_float(value: str | None) -> float:
    if value is None:
        return 25.0
    value = value.strip()
    if not value:
        return 25.0
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        return float(numerator) / float(denominator)
    return float(value)


def _media_duration_from_probe(path: Path) -> float:
    probe = FFProbeMediaProbe()
    metadata = probe.probe(path)
    format_section = metadata.get("format", {})
    duration = format_section.get("duration")
    if duration is None:
        raise ValueError(f"missing media duration: {path}")
    return float(duration)


def read_song_project_id(path: Path | str) -> str | None:
    source = Path(path)
    if not source.exists():
        return None

    text = source.read_text(encoding="utf-8")
    match = _SONG_PROJECT_ID_PATTERN.search(text)
    if match is None:
        return None
    return match.group(1)


def _embed_song_project_id(rendered: str, song_project_id: str) -> str:
    metadata_line = f"  SETANDNOTES_SONG_PROJECT_ID {{{song_project_id}}}"
    lines = rendered.splitlines()

    for index, line in enumerate(lines):
        if _SONG_PROJECT_ID_PATTERN.match(line):
            lines[index] = metadata_line
            return "\n".join(lines)

    if not lines:
        return metadata_line

    insert_at = 1 if len(lines) > 1 else len(lines)
    lines.insert(insert_at, metadata_line)
    return "\n".join(lines)


def _require_active_version(song: Song):
    missing: list[str] = []
    version = None

    if not song.long_name.strip():
        missing.append("song long_name")
    if song.bpm is None:
        missing.append("song bpm")

    try:
        version = song.active_version()
    except ValueError:
        missing.append("active version")

    if version is not None:
        if not version.decoded_tc_start:
            missing.append("decoded tc start")
        if not version.main_audio_path:
            missing.append("main audio path")
        if not version.tc_audio_path:
            missing.append("tc audio path")

    if missing:
        raise ValueError("missing required export values: " + ", ".join(missing))

    return version


def export_song_project(
    song: Song,
    *,
    template_path: Path | str,
    output_dir: Path | str,
    media_duration_provider: Callable[[Path], float] | None = None,
) -> Path:
    version = _require_active_version(song)
    template = TemplateRpp.load(template_path)

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    song_dir = _song_workspace_dir(output_root, song)
    song_dir.mkdir(parents=True, exist_ok=True)
    main_audio_path, tc_audio_path, copied_video_assets = _copy_active_media_files(song_dir, version)
    if version.duration_seconds is not None:
        track_length_seconds = version.duration_seconds
    else:
        duration_provider = media_duration_provider or _media_duration_from_probe
        track_length_seconds = duration_provider(main_audio_path)

    tc_length_seconds = version.duration_seconds if version.duration_seconds is not None else track_length_seconds
    tc_entry_offset_seconds = max(0.0, version.tc_entry_offset_seconds or 0.0)
    project_offset_seconds = _timecode_to_seconds(version.decoded_tc_start or "", _fps_to_float(version.decoded_fps))
    if tc_entry_offset_seconds > 0:
        project_offset_seconds -= tc_entry_offset_seconds

    if template.is_placeholder_template():
        rendered = template.render(
            song_long_name=song.long_name,
            project_offset=f"{project_offset_seconds}",
            bpm=song.bpm or 0.0,
            main_audio_path=str(main_audio_path),
            tc_audio_path=str(tc_audio_path),
        )
    else:
        rendered = template.render_reaper_project(
            project_offset_seconds=project_offset_seconds,
            bpm=song.bpm or 0.0,
            track_media_path=str(main_audio_path),
            tc_media_path=str(tc_audio_path),
            track_length_seconds=track_length_seconds,
            tc_length_seconds=tc_length_seconds,
            track_name=f"{song.long_name}_Track",
            tc_name=f"{song.long_name}_TC",
            tc_entry_offset_seconds=tc_entry_offset_seconds,
            multicam_video_path=str(copied_video_assets["Multicam"]) if "Multicam" in copied_video_assets else None,
            wide_video_path=str(copied_video_assets["WideShot1080"]) if "WideShot1080" in copied_video_assets else None,
            multicam_length_seconds=track_length_seconds if "Multicam" in copied_video_assets else None,
            wide_length_seconds=track_length_seconds if "WideShot1080" in copied_video_assets else None,
            multicam_name=f"{song.long_name}_Multicam",
            wide_name=f"{song.long_name}_Wide",
        )
    rendered = _embed_song_project_id(rendered, song.song_project_id)
    output_path = _song_project_path(song_dir, song)
    output_path.write_text(rendered, encoding="utf-8")
    return output_path
