from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from setandnotes.models.library import Library
from setandnotes.models.song import Song
from setandnotes.models.version import SongVersion
from setandnotes.services.persistence import save_library


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _project_with_song(tmp_path: Path) -> Path:
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


def test_import_dialog_runs_import_for_open_project(tmp_path: Path):
    _app()

    from setandnotes.models.library import Library
    from setandnotes.services.file_classify import ClassifiedMediaFile
    from setandnotes.services.ltc_decode import LtcDecodeResult
    from setandnotes.ui.import_dialog import ImportDialog
    from setandnotes.workers.import_worker import ImportJobResult

    library = Library(project_name="Tour Prep", library_path=str(tmp_path / "tour-set.zeal"))
    source_folder = tmp_path / "Media" / "v2"
    source_folder.mkdir(parents=True)
    foh = source_folder / "Opening Song FOH.wav"
    tc = source_folder / "Opening Song TC.wav"
    foh.write_bytes(b"foh")
    tc.write_bytes(b"tc")

    classified = [
        ClassifiedMediaFile(role="main", normalized_name="opening_song", source_name=str(foh)),
        ClassifiedMediaFile(role="tc", normalized_name="opening_song", source_name=str(tc)),
    ]
    calls: list[tuple[str, str, str | None]] = []

    def run_import_job(*, library, source_folder, version_label=None, source_type="rehearsal", save_path=None):
        calls.append((library.library_path, str(source_folder), str(save_path) if save_path else None))
        updated_library = Library(project_name=library.project_name, library_path=str(save_path), songs=list(library.songs))
        return ImportJobResult(
            library=updated_library,
            source_folder=source_folder,
            version_label=version_label or "v2",
            imported_files=len(classified),
            decoded_files=1,
            saved_path=str(save_path),
            warnings=["Imported 2 files"],
        )

    dialog = ImportDialog(
        library_provider=lambda: library,
        folder_picker=lambda: str(source_folder),
        import_runner=run_import_job,
    )

    results: list[ImportJobResult] = []
    dialog.importCompleted.connect(results.append)
    dialog._choose_folder()
    dialog.import_button.click()

    assert calls == [(str(library.library_path), str(source_folder), str(library.library_path))]
    assert results[0].imported_files == 2
    assert "imported 2 files" in dialog.status_label.text().lower()


def test_import_is_blocked_without_open_project(tmp_path: Path):
    _app()

    from setandnotes.ui.import_dialog import ImportDialog

    source_folder = tmp_path / "Media" / "v2"
    source_folder.mkdir(parents=True)

    dialog = ImportDialog(
        library_provider=lambda: Library(project_name=""),
        folder_picker=lambda: str(source_folder),
        import_runner=lambda **kwargs: None,
    )

    dialog._choose_folder()
    dialog.import_button.click()

    assert "open project" in dialog.status_label.text().lower()


def test_import_result_refreshes_loaded_project_and_status(tmp_path: Path):
    _app()

    from setandnotes.main_window import SetAndNotesMainWindow
    from setandnotes.models.song import Song
    from setandnotes.workers.import_worker import ImportJobResult

    project_path = _project_with_song(tmp_path)
    source_folder = tmp_path / "Media" / "v2"
    source_folder.mkdir(parents=True)
    foh = source_folder / "Opening Song FOH.wav"
    tc = source_folder / "Opening Song TC.wav"
    foh.write_bytes(b"foh")
    tc.write_bytes(b"tc")

    updated_library = Library(project_name="Tour Prep", library_path=str(project_path))
    song = Song(song_id="song-1", long_name="Opening Song", bpm=128.0)
    song.attach_version(
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
    song.attach_version(
        SongVersion(
            version_id="v2",
            song_id="song-1",
            label="v2",
            source_folder=str(source_folder),
            source_type="rehearsal",
            main_audio_path=str(foh),
            tc_audio_path=str(tc),
            decoded_tc_start="01:10:00:00",
        )
    )
    updated_library.add_song(song)

    result = ImportJobResult(
        library=updated_library,
        source_folder=source_folder,
        version_label="v2",
        imported_files=2,
        decoded_files=1,
        saved_path=str(project_path),
        warnings=[],
    )

    class AutoImportDialog:
        def __init__(self, parent=None, *, folder_picker=None, library_provider=None, import_runner=None):
            self.parent = parent
            self.folder_picker = folder_picker
            self.library_provider = library_provider
            self.import_runner = import_runner
            self.importCompleted = []

        def show(self):
            self.parent.handle_import_result(result)

    window = SetAndNotesMainWindow(
        open_library_path_picker=lambda *_: str(project_path),
        save_library_path_picker=lambda *_: None,
        import_folder_picker=lambda *_: str(source_folder),
        template_path_picker=lambda *_: None,
        import_dialog_factory=AutoImportDialog,
    )

    window.open_project_action.trigger()
    window.import_action.trigger()

    assert window.song_table.model().rowCount() == 1
    assert "newer imported version: v2" in window.detail_panel.version_status_label.text().lower()
    assert "imported 2 files" in window.statusBar().currentMessage().lower()


def test_import_dialog_allows_setlist_reorder_before_completion(tmp_path: Path):
    _app()

    from setandnotes.ui.import_dialog import ImportDialog
    from setandnotes.workers.import_worker import ImportJobResult

    project_path = tmp_path / "tour-set.zeal"
    library = Library(project_name="Tour Prep", library_path=str(project_path))
    imported_library = Library(project_name="Tour Prep", library_path=str(project_path))
    imported_library.add_song(Song(song_id="song-a", long_name="Alpha Song", bpm=120.0))
    imported_library.add_song(Song(song_id="song-b", long_name="Beta Song", bpm=121.0))

    result = ImportJobResult(
        library=imported_library,
        source_folder=tmp_path / "Media" / "v2",
        version_label="v2",
        imported_files=4,
        decoded_files=2,
        saved_path=str(project_path),
        warnings=[],
    )

    saved_orders: list[list[str]] = []

    class AutoReorderDialog:
        def __init__(self, parent=None, *, library=None):
            self.library = library

        def exec(self):
            self.library.songs = [self.library.songs[1], self.library.songs[0]]
            return 1

    def fake_save_library(updated_library, path):
        saved_orders.append([song.long_name for song in updated_library.songs])

    dialog = ImportDialog(
        library_provider=lambda: library,
        folder_picker=lambda: str(tmp_path / "Media" / "v2"),
        import_runner=lambda **kwargs: result,
        reorder_dialog_factory=AutoReorderDialog,
        save_library_fn=fake_save_library,
    )

    dialog.set_folder(tmp_path / "Media" / "v2")
    completed: list[ImportJobResult] = []
    dialog.importCompleted.connect(completed.append)

    dialog.import_button.click()

    assert saved_orders[-1] == ["Beta Song", "Alpha Song"]
    assert [song.long_name for song in completed[-1].library.songs] == ["Beta Song", "Alpha Song"]
