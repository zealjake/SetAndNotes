from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from setandnotes.models.rehearsal_notes import SongNoteSection


class NoteEntryDialog(QDialog):
    def __init__(self, note_type: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Add {note_type} Note")
        layout = QVBoxLayout(self)
        self.note_body_input = QTextEdit(self)
        self.note_body_input.setPlaceholderText("Type note")
        self.note_body_input.setFixedHeight(120)
        layout.addWidget(self.note_body_input)

        buttons = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel", self)
        self.save_button = QPushButton("Save", self)
        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self.accept)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)


class NotesPage(QWidget):
    def __init__(
        self,
        parent=None,
        *,
        capture_timestamp_fn: Callable[[], float] | None = None,
        create_note_fn: Callable[[str, str, str, float], dict] | None = None,
    ) -> None:
        super().__init__(parent)
        self._capture_timestamp_fn = capture_timestamp_fn or (lambda: 0.0)
        self._create_note_fn = create_note_fn or (lambda username, note_type, body, timestamp: {})
        self.pending_timestamp: float | None = None
        self.pending_note_type: str | None = None
        self.note_dialog: NoteEntryDialog | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        form_layout = QFormLayout()
        self.username_input = QLineEdit(self)
        form_layout.addRow("Username", self.username_input)
        layout.addLayout(form_layout)

        button_grid = QGridLayout()
        self.general_button = QPushButton("General", self)
        self.lighting_button = QPushButton("Lighting", self)
        self.content_button = QPushButton("Content", self)
        self.cameras_button = QPushButton("Cameras", self)
        self.general_button.clicked.connect(lambda: self._start_note_capture("General"))
        self.lighting_button.clicked.connect(lambda: self._start_note_capture("Lighting/Lasers"))
        self.content_button.clicked.connect(lambda: self._start_note_capture("Content"))
        self.cameras_button.clicked.connect(lambda: self._start_note_capture("Cameras"))
        button_grid.addWidget(self.general_button, 0, 0)
        button_grid.addWidget(self.lighting_button, 0, 1)
        button_grid.addWidget(self.content_button, 1, 0)
        button_grid.addWidget(self.cameras_button, 1, 1)
        layout.addLayout(button_grid)

        self.status_label = QLabel("", self)
        layout.addWidget(self.status_label)

        self.notes_tree = QTreeWidget(self)
        self.notes_tree.setColumnCount(4)
        self.notes_tree.setHeaderLabels(["Time", "User", "Type", "Note"])
        layout.addWidget(self.notes_tree, 1)

    def _start_note_capture(self, note_type: str) -> None:
        try:
            timestamp = self._capture_timestamp_fn()
        except Exception as exc:
            self.status_label.setText(str(exc))
            return

        self.pending_timestamp = timestamp
        self.pending_note_type = note_type
        self.note_dialog = NoteEntryDialog(note_type, self)
        self.note_dialog.accepted.connect(self._confirm_note_dialog)
        self.note_dialog.rejected.connect(self._cancel_note_dialog)
        self.note_dialog.show()

    def _confirm_note_dialog(self) -> None:
        if self.note_dialog is None or self.pending_timestamp is None or self.pending_note_type is None:
            return

        try:
            self._create_note_fn(
                self.username_input.text(),
                self.pending_note_type,
                self.note_dialog.note_body_input.toPlainText(),
                self.pending_timestamp,
            )
        except Exception as exc:
            self.status_label.setText(str(exc))
            return

        self.note_dialog.close()
        self.note_dialog = None
        self.pending_timestamp = None
        self.pending_note_type = None
        self.status_label.setText("Note added to REAPER")

    def _cancel_note_dialog(self) -> None:
        if self.note_dialog is not None:
            self.note_dialog.close()
        self.note_dialog = None
        self.pending_timestamp = None
        self.pending_note_type = None

    def set_note_sections(self, sections: list[SongNoteSection]) -> None:
        self.notes_tree.clear()
        for section in sections:
            song_item = QTreeWidgetItem([section.song_name, "", "", ""])
            self.notes_tree.addTopLevelItem(song_item)
            for note in section.notes:
                song_item.addChild(
                    QTreeWidgetItem(
                        [
                            note.time_text,
                            note.username,
                            note.note_type,
                            note.body,
                        ]
                    )
                )
            song_item.setExpanded(True)
