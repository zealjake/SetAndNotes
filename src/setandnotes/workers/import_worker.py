from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from PySide6.QtCore import QObject, Signal

from setandnotes.models.library import Library
from setandnotes.services.file_classify import ClassifiedMediaFile, classify_media_file
from setandnotes.services.ltc_decode import LtcDecodeResult, decode_ltc_audio
from setandnotes.services.persistence import save_library
from setandnotes.services.song_match import match_imported_files

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


@dataclass(frozen=True, slots=True)
class ImportJobRequest:
    library: Library
    source_folder: Path
    version_label: str | None = None
    source_type: str = "rehearsal"
    save_path: Path | str | None = None


@dataclass(slots=True)
class ImportJobResult:
    library: Library
    source_folder: Path
    version_label: str
    imported_files: int
    decoded_files: int
    saved_path: str
    warnings: list[str] = field(default_factory=list)


DiscoverMediaFiles = Callable[[Path], list[Path]]
ClassifyMediaFile = Callable[[str], ClassifiedMediaFile]
DecodeLtcAudio = Callable[[Path], LtcDecodeResult]
MatchImportedFiles = Callable[..., Library]
SaveLibrary = Callable[[Library, Path | str], None]


def discover_media_files(folder: Path) -> list[Path]:
    return [
        path
        for path in sorted(folder.rglob("*"), key=lambda item: item.relative_to(folder).as_posix())
        if path.is_file() and path.suffix.lower() in SUPPORTED_MEDIA_EXTENSIONS
    ]


def _decode_imported_versions(
    library: Library,
    *,
    source_folder: Path,
    version_label: str,
    decoded_results: dict[str, LtcDecodeResult],
) -> tuple[int, list[str]]:
    decoded_count = 0
    warnings: list[str] = []

    for song in library.songs:
        for version in song.versions:
            if version.source_folder != str(source_folder) or version.label != version_label:
                continue

            if version.tc_audio_path:
                decode_result = decoded_results.get(version.tc_audio_path)
                if decode_result is None:
                    version.status = "warning"
                    version.warnings.append("missing tc decode result")
                    warnings.append(f"{song.long_name}: missing tc decode result")
                    continue

                version.decoded_tc_start = decode_result.first_timecode
                version.decoded_fps = decode_result.fps
                if decode_result.status == "ok":
                    version.status = "warning" if version.warnings else "ready"
                    decoded_count += 1
                else:
                    version.status = "warning"
                    version.warnings.append("tc decode failed")
                    warnings.append(f"{song.long_name}: tc decode failed")

            if version.tc_audio_path and version.decoded_tc_start is None:
                version.status = "warning"
                version.warnings.append("missing decoded tc start")
                warnings.append(f"{song.long_name}: missing decoded tc start")

    return decoded_count, warnings


def run_import_job(
    *,
    library: Library,
    source_folder: Path | str,
    version_label: str | None = None,
    source_type: str = "rehearsal",
    save_path: Path | str | None = None,
    discover_media_files: DiscoverMediaFiles = discover_media_files,
    classify_media_file: ClassifyMediaFile = classify_media_file,
    decode_ltc_audio: DecodeLtcAudio = decode_ltc_audio,
    match_imported_files: MatchImportedFiles = match_imported_files,
    save_library: SaveLibrary = save_library,
) -> ImportJobResult:
    folder = Path(source_folder)
    resolved_version_label = version_label or folder.name
    if save_path is None and not library.library_path:
        raise ValueError("save_path or library.library_path is required")
    resolved_save_path = Path(save_path or library.library_path)

    discovered_files = discover_media_files(folder)
    classified_files: list[ClassifiedMediaFile] = []
    decoded_results: dict[str, LtcDecodeResult] = {}
    warnings: list[str] = []

    for path in discovered_files:
        classified = classify_media_file(str(path))
        if classified.role == "unknown":
            continue

        classified_files.append(classified)
        if classified.role == "tc":
            decode_result = decode_ltc_audio(path)
            decoded_results[str(path)] = decode_result
            if decode_result.status != "ok":
                warnings.append(f"{path.name}: tc decode failed")

    updated_library = match_imported_files(
        library,
        classified_files,
        source_folder=folder,
        version_label=resolved_version_label,
        source_type=source_type,
    )
    decoded_count, decode_warnings = _decode_imported_versions(
        updated_library,
        source_folder=folder,
        version_label=resolved_version_label,
        decoded_results=decoded_results,
    )
    warnings.extend(decode_warnings)

    save_library(updated_library, resolved_save_path)

    return ImportJobResult(
        library=updated_library,
        source_folder=folder,
        version_label=resolved_version_label,
        imported_files=len(classified_files),
        decoded_files=decoded_count,
        saved_path=str(resolved_save_path),
        warnings=warnings,
    )


class ImportWorker(QObject):
    statusChanged = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, request: ImportJobRequest) -> None:
        super().__init__()
        self._request = request

    def run(self) -> ImportJobResult | None:
        self.statusChanged.emit("Importing folder")
        try:
            result = run_import_job(
                library=self._request.library,
                source_folder=self._request.source_folder,
                version_label=self._request.version_label,
                source_type=self._request.source_type,
                save_path=self._request.save_path,
            )
        except Exception as exc:  # pragma: no cover - error propagation
            self.failed.emit(str(exc))
            return None

        self.statusChanged.emit("Import complete")
        self.finished.emit(result)
        return result
