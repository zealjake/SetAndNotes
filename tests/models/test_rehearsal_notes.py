from setandnotes.models.rehearsal_notes import build_song_note_sections


def test_build_song_note_sections_formats_grouped_notes_for_ui() -> None:
    grouped_notes = [
        {
            "song_name": "Intro Song",
            "song_marker_guid": "song-1",
            "song_marker_pos_sec": 60.0,
            "notes": [
                {
                    "guid": "note-1",
                    "pos_sec": 67.125,
                    "username": "Jake",
                    "note_type": "Cameras",
                    "body": "Push in too slow",
                }
            ],
        }
    ]

    sections = build_song_note_sections(grouped_notes, fps=25.0)

    assert len(sections) == 1
    assert sections[0].song_name == "Intro Song"
    assert sections[0].notes[0].guid == "note-1"
    assert sections[0].notes[0].time_text == "00:01:07.125"
    assert sections[0].notes[0].song_time_text == "00:00:07:03"
    assert sections[0].notes[0].username == "Jake"
    assert sections[0].notes[0].note_type == "Cameras"
    assert sections[0].notes[0].body == "Push in too slow"
