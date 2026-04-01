from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RehearsalNote:
    guid: str
    time_text: str
    username: str
    note_type: str
    body: str


@dataclass(slots=True)
class SongNoteSection:
    song_name: str
    song_marker_guid: str
    notes: list[RehearsalNote]


def build_song_note_sections(grouped_notes: list[dict]) -> list[SongNoteSection]:
    sections: list[SongNoteSection] = []
    for group in grouped_notes:
        notes = [
            RehearsalNote(
                guid=str(note.get("guid", "")),
                time_text=format_note_time(float(note.get("pos_sec", 0.0) or 0.0)),
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
