from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QItemSelectionModel, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QComboBox, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QWidget, QSplitter, QToolBar, QVBoxLayout, QTabWidget

from setandnotes.models.library import Library
from setandnotes.models.rehearsal_notes import build_song_note_sections
from setandnotes.services.app_settings import default_app_settings_path, load_app_settings, save_app_settings
from setandnotes.services.persistence import load_library, save_library
from setandnotes.services.reaper_marker_stream import ReaperMarkerStreamClient
from setandnotes.services.reaper_notes import capture_note_timestamp, create_note_marker, fetch_marker_snapshot, group_notes_by_song
from setandnotes.services.touchdesigner_render_import import import_rendered_video_folder
from setandnotes.styles.fonts import activate_application_fonts
from setandnotes.styles.theme import application_stylesheet
from setandnotes.ui.export_dialog import ExportDialog
from setandnotes.ui.import_dialog import ImportDialog
from setandnotes.ui.detail_panel import DetailPanel
from setandnotes.ui.notes_page import NotesPage
from setandnotes.ui.song_table import SongTable
from setandnotes.ui.status_bar import StatusPanel
from setandnotes.workers.import_worker import run_import_job


class _MarkerStreamBridge(QObject):
    markersReceived = Signal(list)
    errorReceived = Signal(str)


class SetAndNotesMainWindow(QMainWindow):
    def __init__(
        self,
        parent=None,
        *,
        open_library_path_picker: Callable[[], str | None] | None = None,
        save_library_path_picker: Callable[[], str | None] | None = None,
        import_folder_picker: Callable[[], str | None] | None = None,
        td_render_folder_picker: Callable[[], str | None] | None = None,
        template_path_picker: Callable[[], str | None] | None = None,
        load_library_fn=load_library,
        save_library_fn=save_library,
        load_app_settings_fn=load_app_settings,
        save_app_settings_fn=save_app_settings,
        capture_note_timestamp_fn=capture_note_timestamp,
        create_note_marker_fn=create_note_marker,
        marker_snapshot_fn=fetch_marker_snapshot,
        marker_stream_factory: Callable[[Callable[[list[dict]], None], Callable[[str], None]], object] | None = None,
        app_settings_path: Path | str | None = None,
        import_dialog_factory=ImportDialog,
        export_dialog_factory=ExportDialog,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("SetAndNotes")
        self.resize(1280, 760)
        self._open_project_path_picker = open_library_path_picker or self._pick_open_project_path
        self._save_project_path_picker = save_library_path_picker or self._pick_save_project_path
        self._import_folder_picker = import_folder_picker or self._pick_import_folder_path
        self._td_render_folder_picker = td_render_folder_picker or self._pick_td_render_folder_path
        self._template_path_picker = template_path_picker or self._pick_template_path
        self._load_library_fn = load_library_fn
        self._save_library_fn = save_library_fn
        self._load_app_settings_fn = load_app_settings_fn
        self._save_app_settings_fn = save_app_settings_fn
        self._capture_note_timestamp_fn = capture_note_timestamp_fn
        self._create_note_marker_fn = create_note_marker_fn
        self._marker_snapshot_fn = marker_snapshot_fn
        self._marker_stream_factory = marker_stream_factory or self._default_marker_stream_factory
        self._app_settings_path = Path(app_settings_path) if app_settings_path is not None else default_app_settings_path()
        self._app_settings = self._load_app_settings_fn(self._app_settings_path)
        self._import_dialog_factory = import_dialog_factory
        self._export_dialog_factory = export_dialog_factory
        self._marker_stream_bridge = _MarkerStreamBridge(self)
        self._marker_stream_bridge.markersReceived.connect(self._apply_marker_snapshot)
        self._marker_stream_bridge.errorReceived.connect(self._handle_marker_stream_error)
        self._marker_stream = self._marker_stream_factory(
            self._marker_stream_bridge.markersReceived.emit,
            self._marker_stream_bridge.errorReceived.emit,
        )
        self._marker_stream_active = False
        self._install_visual_system()
        self._build_toolbar()
        self._build_central_ui()
        self.status_panel = StatusPanel(self)
        self.setStatusBar(self.status_panel)
        self._sync_project_fps_combo()

    def _install_visual_system(self) -> None:
        app = QApplication.instance()
        if app is not None:
            activate_application_fonts(app)
            app.setStyleSheet(application_stylesheet())

    def _build_toolbar(self) -> None:
        project_toolbar = QToolBar("Project", self)
        project_toolbar.setObjectName("projectToolbar")
        project_toolbar.setMovable(False)
        project_toolbar.setFloatable(False)
        self.addToolBar(Qt.TopToolBarArea, project_toolbar)

        self.open_project_action = QAction("Open Project", self)
        self.open_project_action.triggered.connect(self._open_project)
        self.new_project_action = QAction("New Project", self)
        self.new_project_action.triggered.connect(self._create_project)
        self.save_project_action = QAction("Save Project", self)
        self.save_project_action.triggered.connect(self._save_project)
        self.save_project_as_action = QAction("Save Project As", self)
        self.save_project_as_action.triggered.connect(self._save_project_as)
        self.close_project_action = QAction("Close Project", self)
        self.close_project_action.triggered.connect(self._close_project)
        self.import_action = QAction("Import Folder", self)
        self.import_action.triggered.connect(self._open_import_dialog)
        self.import_td_render_action = QAction("Import TD Render Folder", self)
        self.import_td_render_action.triggered.connect(self._import_td_render_folder)
        self.template_action = QAction("Set RPP Template", self)
        self.template_action.triggered.connect(self._set_template_path)
        self.export_action = QAction("Generate Projects", self)
        self.export_action.triggered.connect(self._open_export_dialog)

        self.open_library_action = self.open_project_action
        self.new_library_action = self.new_project_action
        self.save_library_action = self.save_project_action
        self.save_library_as_action = self.save_project_as_action
        self.close_library_action = self.close_project_action

        project_toolbar.addAction(self.new_project_action)
        project_toolbar.addAction(self.open_project_action)
        project_toolbar.addAction(self.save_project_action)
        project_toolbar.addAction(self.save_project_as_action)
        project_toolbar.addAction(self.close_project_action)
        project_toolbar.addSeparator()
        project_toolbar.addWidget(QLabel("Project FPS", self))
        self.project_fps_combo = QComboBox(self)
        self.project_fps_combo.setObjectName("projectFpsCombo")
        self.project_fps_combo.addItems(["25", "30"])
        self.project_fps_combo.currentTextChanged.connect(self._set_project_fps)
        project_toolbar.addWidget(self.project_fps_combo)

        self.addToolBarBreak(Qt.TopToolBarArea)

        workflow_toolbar = QToolBar("Workflow", self)
        workflow_toolbar.setObjectName("workflowToolbar")
        workflow_toolbar.setMovable(False)
        workflow_toolbar.setFloatable(False)
        self.addToolBar(Qt.TopToolBarArea, workflow_toolbar)
        workflow_toolbar.addAction(self.import_action)
        workflow_toolbar.addAction(self.import_td_render_action)
        workflow_toolbar.addAction(self.template_action)
        workflow_toolbar.addAction(self.export_action)

    def _build_central_ui(self) -> None:
        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.main_tabs = QTabWidget(root)
        self.main_tabs.setObjectName("mainTabs")
        self.main_tabs.currentChanged.connect(self._handle_tab_changed)

        setlist_page = QWidget(self.main_tabs)
        setlist_layout = QHBoxLayout(setlist_page)
        setlist_layout.setContentsMargins(0, 0, 0, 0)
        setlist_layout.setSpacing(12)

        splitter = QSplitter(Qt.Horizontal, root)
        self.song_table = SongTable(splitter)
        self.detail_panel = DetailPanel(splitter, audio_path_picker=self._pick_audio_path)
        splitter.addWidget(self.song_table)
        splitter.addWidget(self.detail_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        setlist_layout.addWidget(splitter)

        self.notes_page = NotesPage(
            self.main_tabs,
            capture_timestamp_fn=self._capture_note_timestamp,
            create_note_fn=self._create_rehearsal_note,
        )
        self.notes_page.setObjectName("notesPage")

        self.main_tabs.addTab(setlist_page, "Setlist")
        self.main_tabs.addTab(self.notes_page, "Notes")
        layout.addWidget(self.main_tabs)
        self.setCentralWidget(root)
        self.song_table.selectionModel().selectionChanged.connect(self._sync_detail_panel)
        self.detail_panel.songUpdated.connect(self._refresh_song_row)
        self.detail_panel.rebuildRequested.connect(self._open_rebuild_dialog)
        self._sync_detail_panel()

    def _open_import_dialog(self) -> None:
        library = self._current_library()
        if not library.library_path:
            self.status_panel.set_message("Open a project before importing")
            return

        self._import_dialog = self._import_dialog_factory(
            self,
            folder_picker=self._import_folder_picker,
            library_provider=self._current_library,
            import_runner=run_import_job,
        )
        self._connect_dialog_signal("importCompleted", self.handle_import_result)
        self._connect_dialog_signal("importFailed", self.handle_import_error)
        self._connect_dialog_signal("statusChanged", self.status_panel.set_message)
        self._import_dialog.show()

    def _connect_dialog_signal(self, name: str, handler) -> None:
        signal = getattr(self._import_dialog, name, None)
        connect = getattr(signal, "connect", None)
        if connect is not None:
            connect(handler)

    def _default_marker_stream_factory(
        self,
        on_markers: Callable[[list[dict]], None],
        on_error: Callable[[str], None],
    ) -> ReaperMarkerStreamClient:
        return ReaperMarkerStreamClient(on_markers=on_markers, on_error=on_error)

    def _handle_tab_changed(self, index: int) -> None:
        if self.main_tabs.tabText(index) == "Notes":
            if not self._marker_stream_active:
                self._marker_stream.start()
                self._marker_stream_active = True
            return

        if self._marker_stream_active:
            stop = getattr(self._marker_stream, "stop", None)
            if callable(stop):
                stop()
            self._marker_stream_active = False

    def _capture_note_timestamp(self) -> float:
        return self._capture_note_timestamp_fn()

    def _create_rehearsal_note(self, username: str, note_type: str, body: str, timestamp: float) -> dict:
        result = self._create_note_marker_fn(username, note_type, body, timestamp)
        try:
            markers = self._marker_snapshot_fn()
        except Exception:
            return result
        self._apply_marker_snapshot(markers)
        return result

    def _apply_marker_snapshot(self, markers: list[dict]) -> None:
        grouped = group_notes_by_song(markers)
        self.notes_page.set_note_sections(build_song_note_sections(grouped))
        if self.notes_page.status_label.text() == "REAPER marker stream disconnected":
            self.notes_page.status_label.clear()

    def _handle_marker_stream_error(self, message: str) -> None:
        self.notes_page.status_label.setText(message)

    def _pick_open_project_path(self) -> str | None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            str(self._default_start_dir()),
            filter="SetAndNotes Project (*.zeal)",
        )
        return path or None

    def _pick_open_library_path(self) -> str | None:
        return self._pick_open_project_path()

    def _pick_save_project_path(self) -> str | None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            str(self._default_start_dir() / "setlist.zeal"),
            filter="SetAndNotes Project (*.zeal)",
        )
        return path or None

    def _pick_save_library_path(self) -> str | None:
        return self._pick_save_project_path()

    def _pick_import_folder_path(self) -> str | None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose Import Folder",
            str(self._default_start_dir()),
        )
        return folder or None

    def _pick_td_render_folder_path(self) -> str | None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose TD Render Folder",
            str(self._default_start_dir()),
        )
        return folder or None

    def _pick_template_path(self) -> str | None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Set RPP Template",
            str(self._default_start_dir()),
            "REAPER Project (*.rpp)",
        )
        return path or None

    def _pick_audio_path(self, current_path: str | None) -> str | None:
        start_dir = Path(current_path).parent if current_path else self._default_start_dir()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Audio File",
            str(start_dir),
            "Audio Files (*.wav *.aif *.aiff *.flac *.mp3 *.m4a);;All Files (*)",
        )
        return path or None

    def _default_start_dir(self) -> Path:
        library = self.song_table.model().library()
        if library.library_path:
            return Path(library.library_path).parent
        return Path.cwd()

    def closeEvent(self, event) -> None:
        stop = getattr(self._marker_stream, "stop", None)
        if callable(stop):
            stop()
        super().closeEvent(event)

    def _current_library(self) -> Library:
        return self.song_table.model().library()

    def _current_template_path(self) -> Path | None:
        template_path = self._app_settings.global_rpp_template_path
        if not template_path:
            return None
        path = Path(template_path)
        return path if path.exists() else None

    def global_rpp_template_path(self) -> str | None:
        template_path = self._current_template_path()
        return None if template_path is None else str(template_path)

    def set_app_settings_path(self, path: Path | str) -> None:
        self._app_settings_path = Path(path)
        self._app_settings = self._load_app_settings_fn(self._app_settings_path)

    def _save_app_settings(self) -> None:
        self._save_app_settings_fn(self._app_settings, self._app_settings_path)

    def _set_library(self, library: Library, message: str) -> None:
        self.song_table.model().set_library(library)
        self._sync_project_fps_combo()
        self.song_table.clearSelection()
        if library.songs:
            index = self.song_table.model().index(0, 0)
            selection_model = self.song_table.selectionModel()
            if selection_model is not None:
                selection_model.select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
            self.song_table.setCurrentIndex(index)
        else:
            self.detail_panel.set_song(None)
        self._sync_detail_panel()
        self._update_window_title(library)
        self.status_panel.set_project_path(library.library_path)
        self.status_panel.set_message(message)

    def _sync_project_fps_combo(self) -> None:
        library = self._current_library()
        combo = self.project_fps_combo
        combo.blockSignals(True)
        combo.setCurrentText(library.project_fps if library.project_fps in {"25", "30"} else "25")
        combo.setEnabled(bool(library.library_path))
        combo.blockSignals(False)

    def _update_window_title(self, library: Library) -> None:
        project_name = library.project_name.strip() or "SetAndNotes"
        if library.library_path:
            self.setWindowTitle(f"{project_name} - SetAndNotes")
        else:
            self.setWindowTitle("SetAndNotes")

    def _normalize_project_path(self, path_text: str) -> Path:
        path = Path(path_text)
        if path.suffix.lower() != ".zeal":
            path = path.with_suffix(".zeal")
        return path

    def _create_project(self) -> None:
        path_text = self._save_project_path_picker()
        if not path_text:
            self.status_panel.set_message("New project cancelled")
            return

        path = self._normalize_project_path(path_text)
        library = Library(project_name=path.stem, library_path=str(path))
        self._save_library_fn(library, path)
        self._set_library(library, f"New project created: {path.name}")

    def _create_library(self) -> None:
        self._create_project()

    def _open_project(self) -> None:
        path_text = self._open_project_path_picker()
        if not path_text:
            self.status_panel.set_message("Open project cancelled")
            return

        path = self._normalize_project_path(path_text)
        library = self._load_library_fn(path)
        self._set_library(library, f"Project loaded: {path.name}")

    def _open_library(self) -> None:
        self._open_project()

    def _save_project(self) -> None:
        library = self._current_library()
        if not library.library_path:
            self._save_project_as()
            return

        path = self._normalize_project_path(library.library_path)
        library.library_path = str(path)
        self._save_library_fn(library, path)
        self._set_library(library, f"Project saved: {path.name}")

    def _save_library(self) -> None:
        self._save_project()

    def _save_project_as(self) -> None:
        path_text = self._save_project_path_picker()
        if not path_text:
            self.status_panel.set_message("Save as cancelled")
            return

        library = self._current_library()
        path = self._normalize_project_path(path_text)
        library.library_path = str(path)
        self._save_library_fn(library, path)
        self._set_library(library, f"Project saved as: {path.name}")

    def _save_library_as(self) -> None:
        self._save_project_as()

    def _close_project(self) -> None:
        self.song_table.model().set_library(Library(project_name=""))
        self._sync_project_fps_combo()
        self.song_table.clearSelection()
        self.detail_panel.set_song(None)
        self.status_panel.set_project_path(None)
        self.status_panel.set_message("Project closed")
        self.setWindowTitle("SetAndNotes")

    def _close_library(self) -> None:
        self._close_project()

    def _current_song(self):
        library = self._current_library()
        selection_model = self.song_table.selectionModel()
        if selection_model is None:
            return None

        selected_rows = sorted({index.row() for index in selection_model.selectedRows()})
        if not selected_rows:
            return None

        row = selected_rows[0]
        if 0 <= row < len(library.songs):
            return library.songs[row]
        return None

    def _sync_detail_panel(self, *args) -> None:
        self.detail_panel.set_song(self._current_song())

    def _refresh_song_row(self, song) -> None:
        model = self.song_table.model()
        library = model.library()
        try:
            row = library.songs.index(song)
        except ValueError:
            return

        top_left = model.index(row, 0)
        bottom_right = model.index(row, model.columnCount() - 1)
        model.dataChanged.emit(top_left, bottom_right, [Qt.DisplayRole, Qt.EditRole, Qt.ToolTipRole])

    def _selected_songs(self) -> list:
        library = self._current_library()
        selection_model = self.song_table.selectionModel()
        if selection_model is None:
            return list(library.songs)

        selected_rows = sorted({index.row() for index in selection_model.selectedRows()})
        if not selected_rows:
            return list(library.songs)
        return [library.songs[row] for row in selected_rows if 0 <= row < len(library.songs)]

    def _open_export_dialog(self) -> None:
        self._open_export_dialog_for_songs(self._selected_songs())

    def _import_td_render_folder(self) -> None:
        library = self._current_library()
        if not library.library_path:
            self.status_panel.set_message("Open a project before importing TD renders")
            return

        folder_text = self._td_render_folder_picker()
        if not folder_text:
            self.status_panel.set_message("TD render import cancelled")
            return

        library = import_rendered_video_folder(library, folder_text)
        self._save_library_fn(library, Path(library.library_path))
        self.song_table.model().refresh()
        self._sync_detail_panel()
        self.status_panel.set_message(f"Imported TD renders from {Path(folder_text).name}")

    def _open_rebuild_dialog(self, song) -> None:
        if song is None:
            return
        self._open_export_dialog_for_songs([song])

    def handle_import_result(self, result) -> None:
        message = f"Imported {result.imported_files} files"
        if result.warnings:
            message = f"{message} with {len(result.warnings)} warning(s)"
        self._set_library(result.library, message)

    def handle_import_error(self, message: str) -> None:
        self.status_panel.set_message(message)

    def _open_export_dialog_for_songs(self, songs) -> None:
        if not songs:
            return

        template_path = self._current_template_path()
        if template_path is None:
            self.status_panel.set_message("Set RPP Template first")
            return

        output_dir = self._export_root_for_songs(songs)
        if output_dir is None:
            return
        self._export_dialog = self._export_dialog_factory(
            songs=songs,
            output_dir=output_dir,
            template_path=template_path,
            parent=self,
        )
        self._export_dialog.show()

    def _export_root_for_songs(self, songs) -> Path | None:
        source_folders: list[Path] = []

        for song in songs:
            try:
                version = song.active_version()
            except ValueError:
                self.status_panel.set_message(f"{song.long_name}: select an active version before export")
                return None

            if not version.source_folder:
                self.status_panel.set_message(f"{song.long_name}: missing source folder for export")
                return None

            source_folders.append(Path(version.source_folder))

        if not source_folders:
            self.status_panel.set_message("Select songs before export")
            return None

        first_folder = source_folders[0]
        if any(folder != first_folder for folder in source_folders[1:]):
            self.status_panel.set_message("Selected songs must share the same source folder")
            return None

        return first_folder

    def _set_template_path(self) -> None:
        path_text = self._template_path_picker()
        if not path_text:
            self.status_panel.set_message("Template selection cancelled")
            return

        self._app_settings.global_rpp_template_path = str(Path(path_text))
        self._save_app_settings()
        self.status_panel.set_message(f"Template selected: {Path(path_text).name}")

    def _set_project_fps(self, value: str) -> None:
        if value not in {"25", "30"}:
            return

        library = self._current_library()
        if library.project_fps == value:
            return

        try:
            library.set_project_fps(value)
        except ValueError:
            return

        self.song_table.model().refresh()
        if library.library_path:
            self._save_library_fn(library, Path(library.library_path))
        self._sync_project_fps_combo()
        self._sync_detail_panel()
        self.status_panel.set_message(f"Project FPS set to {value}")
