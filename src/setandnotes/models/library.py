from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from setandnotes.models.song import Song, normalize_fps_label


@dataclass(slots=True)
class Library:
    project_name: str
    project_fps: str = "25"
    songs: list[Song] = field(default_factory=list)
    touchdesigner_sessions: list[dict[str, Any]] = field(default_factory=list)
    library_path: str | None = None

    def add_song(self, song: Song) -> "Library":
        existing_index = next((index for index, existing in enumerate(self.songs) if existing.song_id == song.song_id), None)
        if existing_index is None:
            self.songs.append(song)
        else:
            self.songs[existing_index] = song
        return self

    def set_project_fps(self, value: str | int) -> "Library":
        normalized = normalize_fps_label(str(value))
        if normalized not in {"25", "30"}:
            raise ValueError(f"unsupported project fps: {value}")

        self.project_fps = normalized
        for song in self.songs:
            for version in song.versions:
                version.decoded_fps = normalized
        return self

    def song_by_id(self, song_id: str) -> Song:
        for song in self.songs:
            if song.song_id == song_id:
                return song
        raise KeyError(song_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_fps": self.project_fps,
            "songs": [song.to_dict() for song in self.songs],
            "touchdesigner_sessions": list(self.touchdesigner_sessions),
            "library_path": self.library_path,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Library":
        library = cls(
            project_name=payload["project_name"],
            project_fps=normalize_fps_label(payload.get("project_fps")) or "25",
            library_path=payload.get("library_path"),
        )
        library.songs = [Song.from_dict(song) for song in payload.get("songs", [])]
        library.touchdesigner_sessions = [dict(session) for session in payload.get("touchdesigner_sessions", [])]
        if "project_fps" not in payload:
            derived_project_fps = None
            for song in library.songs:
                if song.active_version_id is None and not song.versions:
                    continue
                try:
                    version = song.active_version()
                except ValueError:
                    version = song.versions[0] if song.versions else None
                if version is None:
                    continue
                derived_project_fps = normalize_fps_label(version.decoded_fps)
                if derived_project_fps in {"25", "30"}:
                    library.project_fps = derived_project_fps
                    break
        return library
