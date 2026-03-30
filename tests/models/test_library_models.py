from setandnotes.models.library import Library
from setandnotes.models.song import Song
from setandnotes.models.version import SongVersion


def test_song_can_attach_and_select_active_version():
    song = Song(song_id="song-1", long_name="Opening Song")
    version = SongVersion(
        version_id="v1",
        song_id="song-1",
        label="prep",
        source_folder="/media/v1",
        source_type="prep",
        main_audio_path="/media/v1/opening_song_foh.wav",
        tc_audio_path="/media/v1/opening_song_tc.wav",
        decoded_tc_start="01:00:00:00",
    )

    updated = song.attach_version(version)

    assert updated.versions == [version]
    assert updated.active_version_id == "v1"
    assert updated.active_version().version_id == "v1"
    assert song.song_project_id


def test_library_round_trips_song_versions_and_active_selection():
    song = Song(song_id="song-1", long_name="Opening Song", bpm=128.0)
    version_1 = SongVersion(
        version_id="v1",
        song_id="song-1",
        label="prep",
        source_folder="/media/v1",
        source_type="prep",
        main_audio_path="/media/v1/opening_song_foh.wav",
        tc_audio_path="/media/v1/opening_song_tc.wav",
        decoded_tc_start="01:00:00:00",
    )
    version_2 = SongVersion(
        version_id="v2",
        song_id="song-1",
        label="rehearsal",
        source_folder="/media/v2",
        source_type="rehearsal",
        main_audio_path="/media/v2/opening_song_foh.wav",
        tc_audio_path="/media/v2/opening_song_tc.wav",
        decoded_tc_start="01:01:00:00",
        tc_entry_offset_seconds=23.0,
    )

    library = Library(project_name="Tour Prep").add_song(
        song.attach_version(version_1).attach_version(version_2).select_active_version("v2")
    )

    payload = library.to_dict()
    restored = Library.from_dict(payload)

    restored_song = restored.song_by_id("song-1")

    assert restored_song.long_name == "Opening Song"
    assert restored_song.song_project_id == song.song_project_id
    assert restored_song.bpm == 128.0
    assert [version.version_id for version in restored_song.versions] == ["v1", "v2"]
    assert restored_song.active_version_id == "v2"
    assert restored_song.active_version().decoded_tc_start == "01:01:00:00"
    assert restored_song.active_version().tc_entry_offset_seconds == 23.0


def test_song_long_name_edit_updates_normalized_name_and_short_name():
    song = Song(song_id="song-1", long_name="Opening Song")

    song.set_long_name("WetLikeBouncerEdit")

    assert song.long_name == "WetLikeBouncerEdit"
    assert song.normalized_name == "wetlikebounceredit"
    assert song.short_name == "WETL"


def test_library_round_trips_touchdesigner_capture_sessions():
    library = Library(project_name="Tour Prep")
    library.touchdesigner_sessions.append(
        {
            "session_name": "BandRehearsal",
            "fps": "25",
            "manifest_path": "/Users/jake/Movies/SetAndNotesCapture/BandRehearsal_session.json",
            "recordings": [
                {
                    "source_id": "camA",
                    "path": "/Users/jake/Movies/SetAndNotesCapture/camA.mov",
                    "tc_start": "01:00:00:00",
                    "tc_end": "01:10:00:00",
                }
            ],
            "events": [{"type": "record_stop", "tc_value": "01:10:00:00"}],
            "markers": [{"song_name": "Marker", "tc_value": "01:05:00:00"}],
        }
    )

    restored = Library.from_dict(library.to_dict())

    assert restored.touchdesigner_sessions[0]["session_name"] == "BandRehearsal"
    assert restored.touchdesigner_sessions[0]["recordings"][0]["source_id"] == "camA"
