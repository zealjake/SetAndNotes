from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from setandnotes.models.version import SongVersion


def _normalize_name(value: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "_" for character in value)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


def _format_imported_long_name(value: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", value)
    return "".join(token[:1].upper() + token[1:].lower() for token in tokens)


def _derive_short_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", value)
    return cleaned[:4].upper()


def normalize_fps_label(value: str | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        if "/" in text:
            numerator, denominator = text.split("/", 1)
            fps_value = float(numerator) / float(denominator)
        else:
            fps_value = float(text)
    except (TypeError, ValueError, ZeroDivisionError):
        return text

    if abs(fps_value - 25.0) < 0.01:
        return "25"
    if abs(fps_value - 30.0) < 0.01:
        return "30"
    if fps_value.is_integer():
        return str(int(fps_value))
    return text


@dataclass(slots=True)
class Song:
    song_id: str
    long_name: str
    song_project_id: str = ""
    normalized_name: str = ""
    short_name: str = ""
    short_name_manual: bool = False
    bpm: float | None = None
    notes: str = ""
    active_version_id: str | None = None
    versions: list[SongVersion] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.song_project_id:
            self.song_project_id = str(uuid.uuid4())
        if not self.normalized_name:
            self.normalized_name = _normalize_name(self.long_name)
        if not self.short_name or not self.short_name_manual:
            self.short_name = _derive_short_name(self.long_name)

    def set_long_name(self, value: str) -> None:
        self.long_name = value
        self.normalized_name = _normalize_name(value)
        if not self.short_name_manual:
            self.short_name = _derive_short_name(value)

    def set_short_name(self, value: str) -> None:
        self.short_name = value
        self.short_name_manual = True

    def attach_version(self, version: SongVersion) -> "Song":
        if version.song_id != self.song_id:
            raise ValueError("version does not belong to this song")

        existing_index = next(
            (index for index, existing in enumerate(self.versions) if existing.version_id == version.version_id),
            None,
        )
        if existing_index is None:
            self.versions.append(version)
        else:
            self.versions[existing_index] = version

        if self.active_version_id is None:
            self.active_version_id = version.version_id
        return self

    def select_active_version(self, version_id: str) -> "Song":
        if not any(version.version_id == version_id for version in self.versions):
            raise ValueError(f"unknown version_id: {version_id}")
        self.active_version_id = version_id
        return self

    def active_version(self) -> SongVersion:
        if self.active_version_id is None:
            raise ValueError("no active version selected")
        for version in self.versions:
            if version.version_id == self.active_version_id:
                return version
        raise ValueError(f"active version not found: {self.active_version_id}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "song_id": self.song_id,
            "long_name": self.long_name,
            "song_project_id": self.song_project_id,
            "normalized_name": self.normalized_name,
            "short_name": self.short_name,
            "short_name_manual": self.short_name_manual,
            "bpm": self.bpm,
            "notes": self.notes,
            "active_version_id": self.active_version_id,
            "versions": [version.to_dict() for version in self.versions],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Song":
        song = cls(
            song_id=payload["song_id"],
            long_name=payload["long_name"],
            song_project_id=payload.get("song_project_id", ""),
            normalized_name=payload.get("normalized_name", ""),
            short_name=payload.get("short_name", ""),
            short_name_manual=payload.get("short_name_manual", False),
            bpm=payload.get("bpm"),
            notes=payload.get("notes", ""),
            active_version_id=payload.get("active_version_id"),
        )
        song.versions = [SongVersion.from_dict(version) for version in payload.get("versions", [])]
        return song
