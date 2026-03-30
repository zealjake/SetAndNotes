from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from setandnotes.models.library import Library
from setandnotes.services.persistence import save_library
from setandnotes.ui.setlist_order_dialog import SetlistOrderDialog
from setandnotes.workers.import_worker import ImportJobResult, run_import_job


class ImportDialog(QDialog):
    importCompleted = Signal(object)
    statusChanged = Signal(str)
    importFailed = Signal(str)

    def __init__(
        self,
        parent=None,
        *,
        folder_picker: Callable[[], str | None] | None = None,
        library_provider: Callable[[], Library | None] | None = None,
        import_runner: Callable[..., ImportJobResult] | None = None,
        reorder_dialog_factory=SetlistOrderDialog,
        save_library_fn: Callable[[Library, Path | str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("importDialog")
        self.setWindowTitle("Import Folder")
        self._folder_picker = folder_picker or self._pick_folder
        self._library_provider = library_provider or self._default_library_provider
        self._import_runner = import_runner or run_import_job
        self._reorder_dialog_factory = reorder_dialog_factory
        self._save_library_fn = save_library_fn or save_library

        self.folder_edit = QLineEdit(self)
        self.folder_edit.setPlaceholderText("Select a media folder")

        browse_button = QPushButton("Browse", self)
        browse_button.clicked.connect(self._choose_folder)

        self.import_button = QPushButton("Import", self)
        self.import_button.clicked.connect(self._run_import)

        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder_edit)
        folder_row.addWidget(browse_button)

        self.status_label = QLabel("Ready", self)

        button_box = QDialogButtonBox(QDialogButtonBox.Close, self)
        button_box.rejected.connect(self.reject)
        button_box.addButton(self.import_button, QDialogButtonBox.AcceptRole)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("Folder", folder_row)
        form.addRow("Status", self.status_label)
        layout.addLayout(form)
        layout.addWidget(button_box)

    def _choose_folder(self) -> None:
        folder = self._folder_picker()
        if not folder:
            self.set_status("Folder selection cancelled")
            return

        self.set_folder(folder)
        self.set_status(f"Selected {Path(folder)}")

    def _default_library_provider(self) -> Library | None:
        return None

    def _run_import(self) -> ImportJobResult | None:
        library = self._library_provider()
        if library is None or not library.library_path:
            message = "Open project first"
            self.set_status(message)
            self.importFailed.emit(message)
            return None

        folder_text = self.folder_edit.text().strip()
        if not folder_text:
            message = "Select an import folder"
            self.set_status(message)
            self.importFailed.emit(message)
            return None
        folder = Path(folder_text).expanduser()

        try:
            result = self._import_runner(
                library=library,
                source_folder=folder,
                save_path=library.library_path,
            )
        except Exception as exc:  # pragma: no cover - surfaced in UI
            message = str(exc)
            self.set_status(message)
            self.importFailed.emit(message)
            return None

        summary = f"Imported {result.imported_files} files"
        if result.warnings:
            summary = f"{summary} with {len(result.warnings)} warning(s)"

        self._maybe_reorder_setlist(result)
        self.set_status(summary)
        self.importCompleted.emit(result)
        return result

    def _maybe_reorder_setlist(self, result: ImportJobResult) -> None:
        if not result.library.songs:
            return

        dialog = self._reorder_dialog_factory(self, library=result.library)
        if dialog.exec():
            self._save_library_fn(result.library, result.saved_path)

    def _pick_folder(self) -> str | None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose Import Folder",
            str(Path.cwd()),
        )
        return folder or None

    def set_folder(self, folder: Path | str) -> None:
        self.folder_edit.setText(str(folder))

    def folder(self) -> Path:
        return Path(self.folder_edit.text()).expanduser()

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
        self.statusChanged.emit(text)
