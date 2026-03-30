from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SongVersion:
    version_id: str
    song_id: str
    label: str
    source_folder: str
    source_type: str
    main_audio_path: str | None = None
    tc_audio_path: str | None = None
    decoded_tc_start: str | None = None
    tc_entry_offset_seconds: float | None = None
    decoded_fps: str | None = None
    decode_confidence: float | None = None
    duration_seconds: float | None = None
    video_assets: dict[str, str] = field(default_factory=dict)
    status: str = "ready"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "song_id": self.song_id,
            "label": self.label,
            "source_folder": self.source_folder,
            "source_type": self.source_type,
            "main_audio_path": self.main_audio_path,
            "tc_audio_path": self.tc_audio_path,
            "decoded_tc_start": self.decoded_tc_start,
            "tc_entry_offset_seconds": self.tc_entry_offset_seconds,
            "decoded_fps": self.decoded_fps,
            "decode_confidence": self.decode_confidence,
            "duration_seconds": self.duration_seconds,
            "video_assets": dict(self.video_assets),
            "status": self.status,
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SongVersion":
        return cls(
            version_id=payload["version_id"],
            song_id=payload["song_id"],
            label=payload["label"],
            source_folder=payload["source_folder"],
            source_type=payload["source_type"],
            main_audio_path=payload.get("main_audio_path"),
            tc_audio_path=payload.get("tc_audio_path"),
            decoded_tc_start=payload.get("decoded_tc_start"),
            tc_entry_offset_seconds=payload.get("tc_entry_offset_seconds"),
            decoded_fps=payload.get("decoded_fps"),
            decode_confidence=payload.get("decode_confidence"),
            duration_seconds=payload.get("duration_seconds"),
            video_assets=dict(payload.get("video_assets", {})),
            status=payload.get("status", "ready"),
            warnings=list(payload.get("warnings", [])),
        )
