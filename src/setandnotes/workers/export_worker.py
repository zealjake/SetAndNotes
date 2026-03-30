from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import Path
from typing import Callable, Sequence

from PySide6.QtCore import QObject, Signal

from setandnotes.models.song import Song
from setandnotes.services.project_export import export_song_project, read_song_project_id
from setandnotes.services.validation import validate_song

_ILLEGAL_FILENAME_CHARS = set('<>:"/\\|?*')


def _sanitize_filename(value: str) -> str:
    sanitized = "".join("_" if character in _ILLEGAL_FILENAME_CHARS else character for character in value)
    sanitized = re.sub(r"[\x00-\x1f]", "_", sanitized).strip()
    return sanitized or "project"


@dataclass(slots=True)
class ExportJobRequest:
    songs: Sequence[Song]
    output_dir: Path | str
    template_path: Path | str
    overwrite: bool = False


@dataclass(slots=True)
class ExportJobResult:
    status: str
    exported_paths: list[Path] = field(default_factory=list)
    invalid_songs: list[str] = field(default_factory=list)
    overwrite_targets: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


ExportSongProject = Callable[..., Path]
PathExists = Callable[[Path], bool]
ReadSongProjectId = Callable[[Path], str | None]


def _export_path(output_dir: Path, song: Song) -> Path:
    song_dir = output_dir / _sanitize_filename(song.long_name)
    return song_dir / f"{_sanitize_filename(song.long_name)}.rpp"


def _song_is_exportable(song: Song) -> tuple[bool, list[str]]:
    validation = validate_song(song)
    messages = list(validation.messages)

    if song.bpm is None and "missing bpm" not in messages:
        messages.append("missing bpm")

    exportable = validation.status != "error" and song.bpm is not None
    return exportable, messages


def run_export_job(
    request: ExportJobRequest,
    *,
    export_song_project: ExportSongProject = export_song_project,
    path_exists: PathExists = Path.exists,
    read_song_project_id_fn: ReadSongProjectId = read_song_project_id,
) -> ExportJobResult:
    output_dir = Path(request.output_dir)
    template_path = Path(request.template_path)

    invalid_songs: list[str] = []
    warnings: list[str] = []
    exportable_songs: list[Song] = []

    for song in request.songs:
        exportable, messages = _song_is_exportable(song)
        if not exportable:
            invalid_songs.append(song.long_name)
            if messages:
                warnings.append(f"{song.long_name}: " + "; ".join(messages))
            continue
        if messages:
            warnings.append(f"{song.long_name}: " + "; ".join(messages))
        exportable_songs.append(song)

    if invalid_songs:
        return ExportJobResult(
            status="error",
            invalid_songs=invalid_songs,
            warnings=warnings,
        )

    overwrite_targets: list[Path] = []
    for song in exportable_songs:
        target = _export_path(output_dir, song)
        if path_exists(target):
            existing_project_id = read_song_project_id_fn(target)
            if existing_project_id is not None and existing_project_id != song.song_project_id:
                return ExportJobResult(
                    status="error",
                    invalid_songs=[song.long_name],
                    warnings=[
                        f"{song.long_name}: existing project belongs to a different song project id"
                    ],
                )
            overwrite_targets.append(target)

    if overwrite_targets and not request.overwrite:
        return ExportJobResult(
            status="needs_confirmation",
            overwrite_targets=overwrite_targets,
            warnings=warnings,
        )

    exported_paths: list[Path] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for song in exportable_songs:
        exported_paths.append(
            export_song_project(
                song,
                template_path=template_path,
                output_dir=output_dir,
            )
        )

    return ExportJobResult(
        status="ok",
        exported_paths=exported_paths,
        warnings=warnings,
    )


class ExportWorker(QObject):
    statusChanged = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        request: ExportJobRequest,
        *,
        export_song_project: ExportSongProject = export_song_project,
        path_exists: PathExists = Path.exists,
    ) -> None:
        super().__init__()
        self._request = request
        self._export_song_project = export_song_project
        self._path_exists = path_exists

    def run(self) -> ExportJobResult | None:
        self.statusChanged.emit("Exporting projects")
        try:
            result = run_export_job(
                self._request,
                export_song_project=self._export_song_project,
                path_exists=self._path_exists,
            )
        except Exception as exc:  # pragma: no cover - error propagation
            self.failed.emit(str(exc))
            return None

        self.statusChanged.emit("Export complete")
        self.finished.emit(result)
        return result
