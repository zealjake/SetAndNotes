from __future__ import annotations

from dataclasses import dataclass
import json

from setandnotes.services.reaper_socket import send_reaper_command


NOTE_TYPE_TO_COLOR_CODE = {
    "Cameras": "0,0,3",
    "Lighting/Lasers": "0,0,4",
    "Content": "0,0,5",
    "General": "0,0,6",
}

NOTE_COLOR_RAW_TO_TYPE = {
    3: "Cameras",
    4: "Lighting/Lasers",
    5: "Content",
    6: "General",
}
NOTE_COLOR_CODE_TO_TYPE = {
    "0,0,3": "Cameras",
    "0,0,4": "Lighting/Lasers",
    "0,0,5": "Content",
    "0,0,6": "General",
}

DEFAULT_MARKER_COLOR_RAW = 0


class ReaperNoteSubmissionError(Exception):
    pass


@dataclass(slots=True)
class ParsedNoteMarker:
    username: str
    note_type: str
    body: str


def format_note_marker_name(username: str, note_type: str, body: str) -> str:
    return f"{username.strip()} - {note_type.strip()} - {body.strip()}"


def note_type_to_color_code(note_type: str) -> str:
    return NOTE_TYPE_TO_COLOR_CODE[note_type]


def is_song_marker(marker: dict) -> bool:
    color_code = str(marker.get("color_code", "") or "").strip()
    if color_code:
        return False
    return int(marker.get("color_raw", DEFAULT_MARKER_COLOR_RAW) or DEFAULT_MARKER_COLOR_RAW) == DEFAULT_MARKER_COLOR_RAW


def is_note_marker(marker: dict) -> bool:
    color_code = str(marker.get("color_code", "") or "").strip()
    if color_code:
        return color_code in NOTE_COLOR_CODE_TO_TYPE
    return int(marker.get("color_raw", -1) or -1) in NOTE_COLOR_RAW_TO_TYPE


def parse_note_marker_name(name: str) -> ParsedNoteMarker | None:
    parts = [part.strip() for part in name.split(" - ", 2)]
    if len(parts) != 3:
        return None
    username, note_type, body = parts
    if note_type not in NOTE_TYPE_TO_COLOR_CODE:
        return None
    return ParsedNoteMarker(username=username, note_type=note_type, body=body)


def group_notes_by_song(markers: list[dict]) -> list[dict]:
    ordered = sorted(markers, key=lambda marker: (float(marker.get("pos_sec", 0.0)), str(marker.get("guid", ""))))
    grouped: list[dict] = []
    current_group: dict | None = None

    for marker in ordered:
        if is_song_marker(marker):
            current_group = {
                "song_name": marker.get("name", ""),
                "song_marker_guid": marker.get("guid", ""),
                "song_marker_pos_sec": float(marker.get("pos_sec", 0.0) or 0.0),
                "notes": [],
            }
            grouped.append(current_group)
            continue

        if not is_note_marker(marker) or current_group is None:
            continue

        parsed = parse_note_marker_name(str(marker.get("name", "")))
        if parsed is None:
            continue

        current_group["notes"].append(
            {
                "guid": marker.get("guid", ""),
                "pos_sec": float(marker.get("pos_sec", 0.0) or 0.0),
                "username": parsed.username,
                "note_type": parsed.note_type,
                "body": parsed.body,
                "color_raw": int(marker.get("color_raw", 0) or 0),
            }
        )

    return grouped


def capture_note_timestamp(*, send_command=send_reaper_command) -> float:
    try:
        playhead_response = send_command("RS_GET_PLAYHEAD")
    except OSError as exc:
        raise ReaperNoteSubmissionError("Unable to reach REAPER") from exc

    return _parse_playhead_response(playhead_response)


def create_note_marker(
    username: str,
    note_type: str,
    body: str,
    pos_sec: float,
    *,
    send_command=send_reaper_command,
) -> dict:
    username = username.strip()
    body = body.strip()

    if not username:
        raise ReaperNoteSubmissionError("Username is required")
    if note_type not in NOTE_TYPE_TO_COLOR_CODE:
        raise ReaperNoteSubmissionError("Note type is required")
    if not body:
        raise ReaperNoteSubmissionError("Note is required")
    marker_name = format_note_marker_name(username, note_type, body)
    marker_payload = json.dumps(
        {
            "name": marker_name,
            "pos_sec": float(pos_sec),
            "color_code": note_type_to_color_code(note_type),
        },
        separators=(",", ":"),
    )

    try:
        marker_response = send_command(f"RS_CREATE_NOTE_MARKER {marker_payload}")
    except OSError as exc:
        raise ReaperNoteSubmissionError("Unable to reach REAPER") from exc

    if not marker_response.startswith("OK"):
        raise ReaperNoteSubmissionError(marker_response or "Marker creation failed")

    return {
        "playhead_sec": float(pos_sec),
        "marker_name": marker_name,
        "marker_response": marker_response,
    }


def _parse_playhead_response(response: str) -> float:
    if not response.startswith("OK "):
        raise ReaperNoteSubmissionError(response or "Malformed REAPER playhead response")

    try:
        payload = json.loads(response[3:])
        playhead_sec = float(payload["playhead_sec"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ReaperNoteSubmissionError("Malformed REAPER playhead response") from exc

    return playhead_sec


def fetch_marker_snapshot(*, send_command=send_reaper_command) -> list[dict]:
    try:
        response = send_command("RS_GET_MARKERS_JSON")
    except OSError as exc:
        raise ReaperNoteSubmissionError("Unable to reach REAPER") from exc

    if not response.startswith("OK "):
        raise ReaperNoteSubmissionError(response or "Malformed REAPER marker response")

    try:
        payload = json.loads(response[3:])
    except json.JSONDecodeError as exc:
        raise ReaperNoteSubmissionError("Malformed REAPER marker response") from exc

    if not isinstance(payload, list):
        raise ReaperNoteSubmissionError("Malformed REAPER marker response")

    return payload
