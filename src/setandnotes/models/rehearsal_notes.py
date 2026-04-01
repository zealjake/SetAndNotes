from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RehearsalNote:
    guid: str
    time_text: str
    song_time_text: str
    username: str
    note_type: str
    body: str


@dataclass(slots=True)
class SongNoteSection:
    song_name: str
    song_marker_guid: str
    notes: list[RehearsalNote]


def build_song_note_sections(grouped_notes: list[dict], *, fps: float = 25.0) -> list[SongNoteSection]:
    sections: list[SongNoteSection] = []
    for group in grouped_notes:
        song_marker_pos_sec = float(group.get("song_marker_pos_sec", 0.0) or 0.0)
        notes = [
            RehearsalNote(
                guid=str(note.get("guid", "")),
                time_text=format_note_time(float(note.get("pos_sec", 0.0) or 0.0)),
                song_time_text=format_note_timecode(max(0.0, float(note.get("pos_sec", 0.0) or 0.0) - song_marker_pos_sec), fps),
                username=str(note.get("username", "")),
                note_type=str(note.get("note_type", "")),
                body=str(note.get("body", "")),
            )
            for note in group.get("notes", [])
        ]
        sections.append(
            SongNoteSection(
                song_name=str(group.get("song_name", "")),
                song_marker_guid=str(group.get("song_marker_guid", "")),
                notes=notes,
            )
        )
    return sections


def format_note_time(pos_sec: float) -> str:
    total_millis = max(0, int(round(pos_sec * 1000)))
    hours, remainder = divmod(total_millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def format_note_timecode(pos_sec: float, fps: float) -> str:
    fps_value = max(1, int(round(fps)))
    total_frames = max(0, int(round(pos_sec * fps_value)))
    frames = total_frames % fps_value
    total_seconds = total_frames // fps_value
    seconds = total_seconds % 60
    total_minutes = total_seconds // 60
    minutes = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
