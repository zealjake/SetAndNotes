from setandnotes.services.reaper_notes import (
    capture_note_timestamp,
    create_note_marker,
    ReaperNoteSubmissionError,
    fetch_marker_snapshot,
    format_note_marker_name,
    group_notes_by_song,
    note_type_to_color_code,
)


def test_format_note_marker_name_uses_required_shape() -> None:
    assert (
        format_note_marker_name("Jake", "Cameras", "Push in too slow")
        == "Jake - Cameras - Push in too slow"
    )


def test_note_type_to_color_code_maps_supported_types() -> None:
    assert note_type_to_color_code("Cameras") == "0,0,3"
    assert note_type_to_color_code("Lighting/Lasers") == "0,0,4"
    assert note_type_to_color_code("Content") == "0,0,5"
    assert note_type_to_color_code("General") == "0,0,6"


def test_group_notes_by_song_uses_nearest_preceding_default_marker() -> None:
    markers = [
        {"guid": "song-1", "pos_sec": 5.0, "name": "Intro Song", "color_raw": 0, "color_code": ""},
        {
            "guid": "note-1",
            "pos_sec": 7.5,
            "name": "Jake - Cameras - Push in too slow",
            "color_raw": 16777219,
            "color_code": "0,0,3",
        },
        {
            "guid": "note-2",
            "pos_sec": 8.0,
            "name": "Liv - General - Band feels flat",
            "color_raw": 16777222,
            "color_code": "0,0,6",
        },
        {"guid": "song-2", "pos_sec": 12.0, "name": "Big Chorus", "color_raw": 0, "color_code": ""},
        {
            "guid": "note-3",
            "pos_sec": 13.25,
            "name": "Jake - Content - Wrong lyric layer",
            "color_raw": 16777221,
            "color_code": "0,0,5",
        },
    ]

    grouped = group_notes_by_song(markers)

    assert [group["song_name"] for group in grouped] == ["Intro Song", "Big Chorus"]
    assert [note["guid"] for note in grouped[0]["notes"]] == ["note-1", "note-2"]
    assert grouped[0]["notes"][0]["username"] == "Jake"
    assert grouped[0]["notes"][0]["note_type"] == "Cameras"
    assert grouped[0]["notes"][1]["body"] == "Band feels flat"
    assert [note["guid"] for note in grouped[1]["notes"]] == ["note-3"]


def test_group_notes_by_song_ignores_default_markers_as_notes() -> None:
    markers = [
        {"guid": "song-1", "pos_sec": 1.0, "name": "Song A", "color_raw": 0},
        {"guid": "song-2", "pos_sec": 2.0, "name": "Song B", "color_raw": 0},
    ]

    grouped = group_notes_by_song(markers)

    assert grouped == [
        {"song_name": "Song A", "song_marker_guid": "song-1", "notes": []},
        {"song_name": "Song B", "song_marker_guid": "song-2", "notes": []},
    ]


def test_capture_note_timestamp_requests_current_playhead() -> None:
    requests: list[str] = []

    def fake_transport(command: str) -> str:
        requests.append(command)
        return 'OK {"playhead_sec":123.456000}'

    result = capture_note_timestamp(send_command=fake_transport)

    assert requests == ["RS_GET_PLAYHEAD"]
    assert result == 123.456


def test_create_note_marker_creates_marker_at_supplied_timestamp() -> None:
    requests: list[str] = []

    def fake_transport(command: str) -> str:
        requests.append(command)
        return 'OK {"marker_id":9,"guid":"note-1"}'

    result = create_note_marker(
        "Jake",
        "Cameras",
        "Push in too slow",
        123.456,
        send_command=fake_transport,
    )

    assert requests == [
        'RS_CREATE_NOTE_MARKER {"name":"Jake - Cameras - Push in too slow","pos_sec":123.456,"color_code":"0,0,3"}',
    ]
    assert result["playhead_sec"] == 123.456
    assert result["marker_response"] == 'OK {"marker_id":9,"guid":"note-1"}'


def test_create_note_marker_rejects_blank_fields() -> None:
    try:
        create_note_marker("", "General", "hello", 12.0, send_command=lambda _: "OK")
    except ReaperNoteSubmissionError as exc:
        assert str(exc) == "Username is required"
    else:
        raise AssertionError("Expected validation error")


def test_capture_note_timestamp_raises_when_playhead_response_is_malformed() -> None:
    def fake_transport(command: str) -> str:
        return "OK {}"

    try:
        capture_note_timestamp(send_command=fake_transport)
    except ReaperNoteSubmissionError as exc:
        assert str(exc) == "Malformed REAPER playhead response"
    else:
        raise AssertionError("Expected malformed response error")


def test_capture_note_timestamp_surfaces_transport_failure() -> None:
    def fake_transport(command: str) -> str:
        raise OSError("connection refused")

    try:
        capture_note_timestamp(send_command=fake_transport)
    except ReaperNoteSubmissionError as exc:
        assert str(exc) == "Unable to reach REAPER"
    else:
        raise AssertionError("Expected transport error")


def test_fetch_marker_snapshot_parses_marker_json_response() -> None:
    snapshot = fetch_marker_snapshot(
        send_command=lambda command: 'OK [{"guid":"song-1","name":"Song 1","pos_sec":1.0,"color_raw":0}]'
    )

    assert snapshot == [{"guid": "song-1", "name": "Song 1", "pos_sec": 1.0, "color_raw": 0}]
