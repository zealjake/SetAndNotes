from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import QApplication

from setandnotes.models.library import Library
from setandnotes.models.song import Song
from setandnotes.models.version import SongVersion


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _song(song_id: str, long_name: str, source_folder: Path) -> Song:
    song = Song(song_id=song_id, long_name=long_name, bpm=128.0)
    song.attach_version(
        SongVersion(
            version_id="v1",
            song_id=song_id,
            label="prep",
            source_folder=str(source_folder),
            source_type="prep",
            main_audio_path=str(source_folder / f"{long_name}.wav"),
            tc_audio_path=str(source_folder / f"{long_name} TC.wav"),
            decoded_tc_start="01:00:00:00",
        )
    )
    return song


def test_export_uses_active_version_source_folder_as_root(tmp_path: Path):
    _app()

    from setandnotes.main_window import SetAndNotesMainWindow

    source_folder = tmp_path / "Imports"
    source_folder.mkdir()
    template_path = tmp_path / "template.rpp"
    template_path.write_text("template", encoding="utf-8")
    project_path = tmp_path / "My Set.zeal"
    library = Library(
        project_name="My Set",
        library_path=str(project_path),
        songs=[_song("song-1", "Opening Song", source_folder)],
    )

    captured: dict[str, Path] = {}

    class ExportDialogStub:
        def __init__(self, *, songs, output_dir, template_path, parent=None):
            captured["output_dir"] = Path(output_dir)
            captured["template_path"] = Path(template_path)
            self.songs = songs

        def show(self):
            return None

    window = SetAndNotesMainWindow(
        open_library_path_picker=lambda *_: str(project_path),
        save_library_path_picker=lambda *_: None,
        import_folder_picker=lambda *_: None,
        template_path_picker=lambda *_: None,
        export_dialog_factory=ExportDialogStub,
    )

    window.song_table.model().set_library(library)
    window._set_library(library, "Project loaded")
    window._app_settings.global_rpp_template_path = str(template_path)
    window._open_export_dialog()

    assert captured["output_dir"] == source_folder


def test_export_blocks_when_selected_songs_have_different_source_folders(tmp_path: Path):
    _app()

    from setandnotes.main_window import SetAndNotesMainWindow

    source_a = tmp_path / "ImportsA"
    source_b = tmp_path / "ImportsB"
    source_a.mkdir()
    source_b.mkdir()
    template_path = tmp_path / "template.rpp"
    template_path.write_text("template", encoding="utf-8")
    project_path = tmp_path / "My Set.zeal"
    library = Library(
        project_name="My Set",
        library_path=str(project_path),
        songs=[
            _song("song-1", "Opening Song", source_a),
            _song("song-2", "Second Song", source_b),
        ],
    )

    class ExportDialogStub:
        def __init__(self, **kwargs):
            raise AssertionError("export dialog should not open for mixed source folders")

    window = SetAndNotesMainWindow(
        open_library_path_picker=lambda *_: str(project_path),
        save_library_path_picker=lambda *_: None,
        import_folder_picker=lambda *_: None,
        template_path_picker=lambda *_: None,
        export_dialog_factory=ExportDialogStub,
    )

    window.song_table.model().set_library(library)
    window._set_library(library, "Project loaded")
    window._app_settings.global_rpp_template_path = str(template_path)

    selection_model = window.song_table.selectionModel()
    selection_model.select(
        window.song_table.model().index(0, 0),
        QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
    )
    selection_model.select(
        window.song_table.model().index(1, 0),
        QItemSelectionModel.Select | QItemSelectionModel.Rows,
    )

    window._open_export_dialog()

    assert "same source folder" in window.statusBar().currentMessage().lower()
