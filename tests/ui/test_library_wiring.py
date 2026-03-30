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


def _library_with_song(tmp_path: Path) -> Path:
    project_path = tmp_path / "tour-set.zeal"
    project = Library(project_name="Tour Prep", library_path=str(project_path))
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


def test_new_library_action_creates_file_and_refreshes_ui(tmp_path: Path):
    _app()

    from setandnotes.main_window import SetAndNotesMainWindow

    project_path = tmp_path / "new-project.zeal"

    window = SetAndNotesMainWindow(
        open_library_path_picker=lambda *_: None,
        save_library_path_picker=lambda *_: str(project_path),
        import_folder_picker=lambda *_: None,
        template_path_picker=lambda *_: None,
        load_library_fn=load_library,
        save_library_fn=save_library,
    )

    window.new_project_action.trigger()

    assert project_path.exists()
    assert window.song_table.model().library().library_path == str(project_path)
    assert window.song_table.model().rowCount() == 0
    assert "new-project.zeal" in window.statusBar().currentMessage()


def test_open_library_action_loads_rows_and_selects_first_song(tmp_path: Path):
    _app()

    from setandnotes.main_window import SetAndNotesMainWindow

    library_path = _library_with_song(tmp_path)

    window = SetAndNotesMainWindow(
        open_library_path_picker=lambda *_: str(library_path),
        save_library_path_picker=lambda *_: None,
        import_folder_picker=lambda *_: None,
        template_path_picker=lambda *_: None,
        load_library_fn=load_library,
        save_library_fn=save_library,
    )

    window.open_project_action.trigger()

    assert window.song_table.model().rowCount() == 1
    assert window.detail_panel.song_title_label.text() == "Opening Song"
    assert "tour-set.zeal" in window.statusBar().currentMessage()


def test_template_action_updates_loaded_library_and_persists(tmp_path: Path):
    _app()

    from setandnotes.main_window import SetAndNotesMainWindow
    from setandnotes.services.app_settings import load_app_settings

    library_path = _library_with_song(tmp_path)
    template_path = tmp_path / "template.rpp"
    template_path.write_text("template", encoding="utf-8")
    settings_path = tmp_path / "settings.json"

    window = SetAndNotesMainWindow(
        open_library_path_picker=lambda *_: str(library_path),
        save_library_path_picker=lambda *_: None,
        import_folder_picker=lambda *_: None,
        template_path_picker=lambda *_: str(template_path),
        load_library_fn=load_library,
        save_library_fn=save_library,
        app_settings_path=settings_path,
    )

    window.open_project_action.trigger()
    window.template_action.trigger()

    assert window.global_rpp_template_path() == str(template_path)
    assert load_app_settings(settings_path).global_rpp_template_path == str(template_path)
    assert load_library(library_path).project_name == "Tour Prep"
    assert "template.rpp" in window.statusBar().currentMessage()


def test_template_setting_survives_a_restarted_window(tmp_path: Path):
    _app()

    from setandnotes.main_window import SetAndNotesMainWindow

    template_path = tmp_path / "template.rpp"
    template_path.write_text("template", encoding="utf-8")
    settings_path = tmp_path / "settings.json"

    first_window = SetAndNotesMainWindow(
        open_library_path_picker=lambda *_: None,
        save_library_path_picker=lambda *_: None,
        import_folder_picker=lambda *_: None,
        template_path_picker=lambda *_: str(template_path),
        load_library_fn=load_library,
        save_library_fn=save_library,
        app_settings_path=settings_path,
    )
    first_window.template_action.trigger()

    second_window = SetAndNotesMainWindow(
        open_library_path_picker=lambda *_: None,
        save_library_path_picker=lambda *_: None,
        import_folder_picker=lambda *_: None,
        template_path_picker=lambda *_: None,
        load_library_fn=load_library,
        save_library_fn=save_library,
        app_settings_path=settings_path,
    )

    assert second_window.global_rpp_template_path() == str(template_path)


def test_import_dialog_browse_uses_injected_folder_picker(tmp_path: Path):
    _app()

    from setandnotes.ui.import_dialog import ImportDialog

    folder = tmp_path / "Media" / "v2"
    folder.mkdir(parents=True)

    dialog = ImportDialog(folder_picker=lambda: str(folder))
    dialog._choose_folder()

    assert dialog.folder_edit.text() == str(folder)
    assert dialog.status_label.text() == f"Selected {folder}"


def test_import_td_render_folder_updates_active_version_video_assets(tmp_path: Path):
    _app()

    from setandnotes.main_window import SetAndNotesMainWindow
    from setandnotes.services.persistence import load_library

    project_path = _library_with_song(tmp_path)
    render_folder = tmp_path / "TDRender" / "v1"
    render_folder.mkdir(parents=True)
    (render_folder / "Opening Song_Multicam_TC01_00_00_00.mov").write_bytes(b"multicam")

    window = SetAndNotesMainWindow(
        open_library_path_picker=lambda *_: str(project_path),
        save_library_path_picker=lambda *_: None,
        import_folder_picker=lambda *_: None,
        template_path_picker=lambda *_: None,
        td_render_folder_picker=lambda *_: str(render_folder),
        load_library_fn=load_library,
        save_library_fn=save_library,
    )

    window.open_project_action.trigger()
    window.import_td_render_action.trigger()

    version = window.song_table.model().library().song_by_id("song-1").active_version()
    assert version.video_assets["Multicam"] == str(render_folder / "Opening Song_Multicam_TC01_00_00_00.mov")
    assert window.detail_panel.multicam_video_input.text() == str(
        render_folder / "Opening Song_Multicam_TC01_00_00_00.mov"
    )
    assert "Imported TD renders" in window.statusBar().currentMessage()
