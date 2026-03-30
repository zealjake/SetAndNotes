from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import QApplication

from setandnotes.models.library import Library
from setandnotes.models.song import Song
from setandnotes.models.version import SongVersion


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _library() -> Library:
    song_ready = Song(song_id="song-1", long_name="Opening Song", bpm=128.0)
    song_ready.attach_version(
        SongVersion(
            version_id="v1",
            song_id="song-1",
            label="prep",
            source_folder="/media/v1",
            source_type="prep",
            main_audio_path="/media/v1/opening_foh.wav",
            tc_audio_path="/media/v1/opening_tc.wav",
            decoded_tc_start="01:00:00:00",
            decoded_fps="25/1",
        )
    )
    song_ready.attach_version(
        SongVersion(
            version_id="v2",
            song_id="song-1",
            label="rehearsal",
            source_folder="/media/v2",
            source_type="rehearsal",
            main_audio_path="/media/v2/opening_foh.wav",
            tc_audio_path="/media/v2/opening_tc.wav",
            decoded_tc_start="01:10:00:00",
            decoded_fps="30/1",
        )
    )

    song_problem = Song(song_id="song-2", long_name="Broken Song")
    song_problem.attach_version(
        SongVersion(
            version_id="v2",
            song_id="song-2",
            label="rehearsal",
            source_folder="/media/v2",
            source_type="rehearsal",
            main_audio_path="/media/v2/broken_foh.wav",
            tc_audio_path=None,
            decoded_tc_start=None,
            decoded_fps="30/1",
            warnings=["missing tc decode"],
            status="warning",
        )
    )

    return Library(project_name="Tour Prep", songs=[song_ready, song_problem])


def _duplicate_library() -> Library:
    song_duplicate = Song(song_id="song-3", long_name="Opening Song", bpm=128.0)
    song_duplicate.attach_version(
        SongVersion(
            version_id="v3",
            song_id="song-3",
            label="rehearsal-2",
            source_folder="/media/v3",
            source_type="rehearsal",
            main_audio_path="/media/v3/opening_foh.wav",
            tc_audio_path="/media/v3/opening_tc.wav",
            decoded_tc_start="01:00:00:00",
            decoded_fps="25/1",
        )
    )

    song_short_duplicate = Song(song_id="song-4", long_name="Openingsong", bpm=128.0)
    song_short_duplicate.attach_version(
        SongVersion(
            version_id="v4",
            song_id="song-4",
            label="rehearsal-3",
            source_folder="/media/v4",
            source_type="rehearsal",
            main_audio_path="/media/v4/opening_foh.wav",
            tc_audio_path="/media/v4/opening_tc.wav",
            decoded_tc_start="01:10:00:00",
            decoded_fps="30/1",
        )
    )

    return Library(project_name="Tour Prep", songs=[song_duplicate, song_short_duplicate])


def _duplicate_tc_library() -> Library:
    song_a = Song(song_id="song-5", long_name="Second Song", bpm=128.0)
    song_a.attach_version(
        SongVersion(
            version_id="v5",
            song_id="song-5",
            label="rehearsal-4",
            source_folder="/media/v5",
            source_type="rehearsal",
            main_audio_path="/media/v5/second_foh.wav",
            tc_audio_path="/media/v5/second_tc.wav",
            decoded_tc_start="01:20:00:00",
            decoded_fps="25/1",
        )
    )

    song_b = Song(song_id="song-6", long_name="Third Song", bpm=128.0)
    song_b.attach_version(
        SongVersion(
            version_id="v6",
            song_id="song-6",
            label="rehearsal-5",
            source_folder="/media/v6",
            source_type="rehearsal",
            main_audio_path="/media/v6/third_foh.wav",
            tc_audio_path="/media/v6/third_tc.wav",
            decoded_tc_start="01:20:00:00",
            decoded_fps="30/1",
        )
    )

    return Library(project_name="Tour Prep", songs=[song_a, song_b])


def _duplicate_long_name_library() -> Library:
    song_a = Song(song_id="song-7", long_name="Opening Song", bpm=128.0)
    song_a.attach_version(
        SongVersion(
            version_id="v7",
            song_id="song-7",
            label="rehearsal-6",
            source_folder="/media/v7",
            source_type="rehearsal",
            main_audio_path="/media/v7/opening_foh.wav",
            tc_audio_path="/media/v7/opening_tc.wav",
            decoded_tc_start="01:30:00:00",
            decoded_fps="25/1",
        )
    )

    song_b = Song(song_id="song-8", long_name="Opening Song", bpm=128.0)
    song_b.attach_version(
        SongVersion(
            version_id="v8",
            song_id="song-8",
            label="rehearsal-7",
            source_folder="/media/v8",
            source_type="rehearsal",
            main_audio_path="/media/v8/opening_foh.wav",
            tc_audio_path="/media/v8/opening_tc.wav",
            decoded_tc_start="01:40:00:00",
            decoded_fps="30/1",
        )
    )

    return Library(project_name="Tour Prep", songs=[song_a, song_b])


def test_setlist_table_model_exposes_expected_columns():
    _app()

    from setandnotes.models.setlist_table_model import SetlistTableModel

    model = SetlistTableModel(_library())

    assert model.rowCount() == 2
    assert model.columnCount() == 8
    assert [model.headerData(index, Qt.Horizontal, Qt.DisplayRole) for index in range(model.columnCount())] == [
        "Song ID",
        "Long Name",
        "Short Name",
        "BPM",
        "TC Hour",
        "FPS",
        "Status",
        "Version",
    ]
    assert model.data(model.index(0, 0), Qt.DisplayRole) == "1"
    assert model.data(model.index(0, 1), Qt.DisplayRole) == "Opening Song"
    assert model.data(model.index(0, 2), Qt.DisplayRole) == "OPEN"
    assert model.data(model.index(0, 3), Qt.DisplayRole) == "128.0"
    assert model.data(model.index(0, 4), Qt.DisplayRole) == "01:00:00:00"
    assert model.data(model.index(0, 5), Qt.DisplayRole) == "25"
    assert model.data(model.index(0, 6), Qt.DisplayRole) == "ok"
    assert model.data(model.index(1, 0), Qt.DisplayRole) == "2"
    assert model.data(model.index(1, 6), Qt.DisplayRole) == "error"
    assert model.data(model.index(0, 7), Qt.DisplayRole) == "v1"


def test_setlist_table_model_allows_editing_song_name_and_bpm():
    _app()

    from setandnotes.models.setlist_table_model import SetlistTableModel

    library = _library()
    model = SetlistTableModel(library)

    assert model.setData(model.index(0, 1), "Intro Song", Qt.EditRole)
    assert model.setData(model.index(0, 2), "INTRO", Qt.EditRole)
    assert model.setData(model.index(0, 7), "v2", Qt.EditRole)
    assert model.setData(model.index(0, 3), "132", Qt.EditRole)
    assert model.setData(model.index(0, 4), "01:02:03:04", Qt.EditRole)
    assert model.setData(model.index(0, 5), "30", Qt.EditRole)

    assert library.song_by_id("song-1").short_name == "INTRO"
    assert library.song_by_id("song-1").long_name == "Intro Song"
    assert library.song_by_id("song-1").bpm == 132.0
    assert library.song_by_id("song-1").active_version_id == "v2"
    assert library.song_by_id("song-1").active_version().decoded_fps == "30"
    assert library.song_by_id("song-1").active_version().decoded_tc_start == "01:02:03:04"
    assert model.data(model.index(0, 1), Qt.DisplayRole) == "Intro Song"
    assert model.data(model.index(0, 2), Qt.DisplayRole) == "INTRO"
    assert model.data(model.index(0, 3), Qt.DisplayRole) == "132.0"
    assert model.data(model.index(0, 5), Qt.DisplayRole) == "30"
    assert model.data(model.index(0, 7), Qt.DisplayRole) == "v2"


def test_project_fps_overwrites_all_song_versions():
    library = _library()

    assert library.project_fps == "25"

    library.set_project_fps("30")

    assert library.project_fps == "30"
    assert library.song_by_id("song-1").active_version().decoded_fps == "30"
    assert library.song_by_id("song-2").active_version().decoded_fps == "30"


def test_setlist_table_model_highlights_duplicate_names_and_tc_starts():
    _app()

    from setandnotes.models.setlist_table_model import SetlistTableModel

    model = SetlistTableModel(_duplicate_library())

    assert model.data(model.index(0, 6), Qt.DisplayRole) == "warning"
    assert model.data(model.index(1, 6), Qt.DisplayRole) == "warning"
    assert "duplicate short name" in model.data(model.index(0, 0), Qt.ToolTipRole).lower()
    assert "duplicate short name" in model.data(model.index(1, 0), Qt.ToolTipRole).lower()


def test_setlist_table_model_marks_duplicate_tc_starts_as_errors():
    _app()

    from setandnotes.models.setlist_table_model import SetlistTableModel

    model = SetlistTableModel(_duplicate_tc_library())

    assert model.data(model.index(0, 6), Qt.DisplayRole) == "error"
    assert model.data(model.index(1, 6), Qt.DisplayRole) == "error"
    assert "duplicate tc start" in model.data(model.index(0, 0), Qt.ToolTipRole).lower()


def test_setlist_table_model_marks_duplicate_long_names_as_errors():
    _app()

    from setandnotes.models.setlist_table_model import SetlistTableModel

    model = SetlistTableModel(_duplicate_long_name_library())

    assert model.data(model.index(0, 6), Qt.DisplayRole) == "error"
    assert model.data(model.index(1, 6), Qt.DisplayRole) == "error"
    assert "duplicate long name" in model.data(model.index(0, 0), Qt.ToolTipRole).lower()


def test_validation_service_returns_blocking_and_warning_states():
    _app()

    from setandnotes.services.validation import validate_song

    ready = _library().song_by_id("song-1")
    problem = _library().song_by_id("song-2")

    ready_result = validate_song(ready)
    problem_result = validate_song(problem)

    assert ready_result.status == "ok"
    assert ready_result.messages == ()
    assert problem_result.status == "error"
    assert any("tc audio" in message.lower() for message in problem_result.messages)


def test_status_column_exposes_visual_roles():
    _app()

    from setandnotes.models.setlist_table_model import SetlistColumns, SetlistTableModel

    model = SetlistTableModel(_library())

    ok_index = model.index(0, SetlistColumns.STATUS)
    error_index = model.index(1, SetlistColumns.STATUS)

    assert model.data(ok_index, Qt.TextAlignmentRole) == int(Qt.AlignCenter)
    assert isinstance(model.data(ok_index, Qt.BackgroundRole), QBrush)
    assert isinstance(model.data(error_index, Qt.BackgroundRole), QBrush)
    assert model.data(ok_index, Qt.BackgroundRole).color().name().lower() != model.data(
        error_index, Qt.BackgroundRole
    ).color().name().lower()
