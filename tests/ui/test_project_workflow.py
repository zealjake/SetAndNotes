from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from setandnotes.models.library import Library
from setandnotes.models.song import Song
from setandnotes.models.version import SongVersion
from setandnotes.services.persistence import load_library, save_library


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _project_with_song(tmp_path: Path) -> Path:
    project_path = tmp_path / "tour-set.zeal"
    project = Library(project_name="Tour Set", library_path=str(project_path))
    project.add_song(
        Song(song_id="song-1", long_name="Opening Song", bpm=128.0).attach_version(
            SongVersion(
                version_id="v1",
                song_id="song-1",
                label="prep",
                source_folder="/media/v1",
                source_type="prep",
                main_audio_path="/media/v1/opening_foh.wav",
                tc_audio_path="/media/v1/opening_tc.wav",
                decoded_tc_start="01:00:00:00",
            )
        )
    )
    save_library(project, project_path)
    return project_path


def test_project_actions_use_zeal_labels_and_filters(tmp_path: Path, monkeypatch):
    _app()

    from setandnotes.main_window import SetAndNotesMainWindow

    picked_paths: list[str] = []

    def fake_get_open_file_name(*args, **kwargs):
        picked_paths.append(kwargs.get("filter", ""))
        return str(tmp_path / "open.zeal"), ""

    def fake_get_save_file_name(*args, **kwargs):
        picked_paths.append(kwargs.get("filter", ""))
        return str(tmp_path / "save.zeal"), ""

    monkeypatch.setattr("setandnotes.main_window.QFileDialog.getOpenFileName", fake_get_open_file_name)
    monkeypatch.setattr("setandnotes.main_window.QFileDialog.getSaveFileName", fake_get_save_file_name)

    window = SetAndNotesMainWindow(
        open_library_path_picker=None,
        save_library_path_picker=None,
        import_folder_picker=lambda: None,
        template_path_picker=lambda: None,
        load_library_fn=load_library,
        save_library_fn=save_library,
    )

    assert window.new_project_action.text() == "New Project"
    assert window.open_project_action.text() == "Open Project"
    assert window.save_project_action.text() == "Save Project"
    assert window.save_project_as_action.text() == "Save Project As"
    assert window.close_project_action.text() == "Close Project"

    window._pick_open_library_path()
    window._pick_save_library_path()

    assert any(".zeal" in filter_text for filter_text in picked_paths)


def test_save_project_as_switches_current_project_path(tmp_path: Path):
    _app()

    from setandnotes.main_window import SetAndNotesMainWindow

    original_path = _project_with_song(tmp_path)
    new_path = tmp_path / "tour-set-copy.zeal"

    window = SetAndNotesMainWindow(
        open_library_path_picker=lambda: str(original_path),
        save_library_path_picker=lambda: str(new_path),
        import_folder_picker=lambda: None,
        template_path_picker=lambda: None,
        load_library_fn=load_library,
        save_library_fn=save_library,
    )

    window.open_project_action.trigger()
    window.save_project_as_action.trigger()

    assert window.song_table.model().library().library_path == str(new_path)
    assert new_path.exists()
    assert "tour-set-copy.zeal" in window.statusBar().currentMessage()


def test_close_project_clears_loaded_state(tmp_path: Path):
    _app()

    from setandnotes.main_window import SetAndNotesMainWindow

    project_path = _project_with_song(tmp_path)

    window = SetAndNotesMainWindow(
        open_library_path_picker=lambda: str(project_path),
        save_library_path_picker=lambda: None,
        import_folder_picker=lambda: None,
        template_path_picker=lambda: None,
        load_library_fn=load_library,
        save_library_fn=save_library,
    )

    window.open_project_action.trigger()
    window.close_project_action.trigger()

    assert window.song_table.model().rowCount() == 0
    assert window.song_table.model().library().library_path is None
    assert "closed" in window.statusBar().currentMessage().lower()


def test_project_fps_combo_updates_library_and_persists(tmp_path: Path):
    _app()

    from setandnotes.main_window import SetAndNotesMainWindow
    from setandnotes.services.persistence import load_library

    project_path = _project_with_song(tmp_path)

    window = SetAndNotesMainWindow(
        open_library_path_picker=lambda: str(project_path),
        save_library_path_picker=lambda: None,
        import_folder_picker=lambda: None,
        template_path_picker=lambda: None,
        load_library_fn=load_library,
        save_library_fn=save_library,
    )

    window.open_project_action.trigger()
    window.project_fps_combo.setCurrentText("30")

    assert window.song_table.model().library().project_fps == "30"
    assert window.song_table.model().library().song_by_id("song-1").active_version().decoded_fps == "30"
    assert load_library(project_path).project_fps == "30"
