from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class RecordingRange:
    source_id: str
    path: str
    tc_start: str
    tc_end: str | None = None


@dataclass(slots=True)
class SongMarker:
    song_name: str
    tc_value: str


@dataclass(slots=True)
class CaptureSessionState:
    session_name: str
    fps: str
    output_root: Path
    recordings: list[RecordingRange] = field(default_factory=list)
    markers: list[SongMarker] = field(default_factory=list)
    active_recordings: dict[str, RecordingRange] = field(default_factory=dict)
    is_recording: bool = False


class CaptureController:
    def __init__(self, *, session_name: str, output_root: Path | str, fps: str) -> None:
        self._state = CaptureSessionState(
            session_name=session_name,
            fps=str(fps),
            output_root=Path(output_root),
        )

    @property
    def state(self) -> CaptureSessionState:
        return self._state

    def build_record_path(self, source_id: str, *, timestamp_token: str | None = None, extension: str = ".mov") -> Path:
        token = timestamp_token or datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_source = "".join(character for character in source_id if character.isalnum() or character in {"_", "-"})
        return self._state.output_root / f"{safe_source}_{token}{extension}"

    def start_recording(self, *, tc_start: str, source_paths: dict[str, Path | str]) -> None:
        if self._state.is_recording:
            raise RuntimeError("Capture session is already recording")

        self._state.recordings = []
        self._state.active_recordings = {}
        for source_id, path in source_paths.items():
            entry = RecordingRange(source_id=source_id, path=str(path), tc_start=tc_start)
            self._state.recordings.append(entry)
            self._state.active_recordings[source_id] = entry
        self._state.is_recording = True

    def stop_recording(self, *, tc_end: str) -> None:
        if not self._state.is_recording:
            raise RuntimeError("Capture session is not recording")

        for entry in self._state.active_recordings.values():
            entry.tc_end = tc_end
        self._state.active_recordings = {}
        self._state.is_recording = False

    def add_marker(self, song_name: str, *, tc_value: str) -> None:
        self._state.markers.append(SongMarker(song_name=song_name, tc_value=tc_value))

    def build_manifest(self) -> dict[str, object]:
        return {
            "session_name": self._state.session_name,
            "fps": self._state.fps,
            "output_root": str(self._state.output_root),
            "recordings": [asdict(entry) for entry in self._state.recordings],
            "markers": [asdict(entry) for entry in self._state.markers],
        }

    def write_manifest(self, path: Path | str | None = None) -> Path:
        target = Path(path) if path is not None else self._state.output_root / f"{self._state.session_name}_session.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.build_manifest(), indent=2) + "\n", encoding="utf-8")
        return target
