from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
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
        add_web_user_fn: Callable[[str], None] | None = None,
        update_web_user_fn: Callable[[str, str, bool], None] | None = None,
        copy_all_links_fn: Callable[[], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._capture_timestamp_fn = capture_timestamp_fn or (lambda: 0.0)
        self._create_note_fn = create_note_fn or (lambda username, note_type, body, timestamp: {})
        self._add_web_user_fn = add_web_user_fn or (lambda username: None)
        self._update_web_user_fn = update_web_user_fn or (lambda token, username, enabled: None)
        self._copy_all_links_fn = copy_all_links_fn or (lambda: "")
        self.pending_timestamp: float | None = None
        self.pending_note_type: str | None = None
        self.note_dialog: NoteEntryDialog | None = None
        self._syncing_web_users = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        form_layout = QFormLayout()
        self.username_input = QLineEdit(self)
        form_layout.addRow("Username", self.username_input)
        layout.addLayout(form_layout)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        capture_group = QGroupBox("Capture Notes", self)
        capture_layout = QVBoxLayout(capture_group)
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
        capture_layout.addLayout(button_grid)
        self.status_label = QLabel("", self)
        capture_layout.addWidget(self.status_label)
        top_row.addWidget(capture_group, 1)

        web_group = QGroupBox("Web Note Users", self)
        web_layout = QVBoxLayout(web_group)
        web_user_form = QHBoxLayout()
        self.web_user_name_input = QLineEdit(self)
        self.web_user_name_input.setPlaceholderText("Add web note username")
        self.add_web_user_button = QPushButton("Add Web User", self)
        self.add_web_user_button.clicked.connect(self._add_web_user)
        web_user_form.addWidget(self.web_user_name_input, 1)
        web_user_form.addWidget(self.add_web_user_button)
        self.copy_all_web_users_button = QPushButton("Copy All", self)
        self.copy_all_web_users_button.clicked.connect(self._copy_all_links)
        web_user_form.addWidget(self.copy_all_web_users_button)
        web_layout.addLayout(web_user_form)

        self.web_users_tree = QTreeWidget(self)
        self.web_users_tree.setColumnCount(4)
        self.web_users_tree.setHeaderLabels(["Username", "Enabled", "Link", "Copy"])
        web_layout.addWidget(self.web_users_tree)
        top_row.addWidget(web_group, 1)

        layout.addLayout(top_row)

        self.notes_tree = QTreeWidget(self)
        self.notes_tree.setColumnCount(5)
        self.notes_tree.setHeaderLabels(["Time", "Song Time", "User", "Type", "Note"])
        layout.addWidget(self.notes_tree, 1)

    def _add_web_user(self) -> None:
        username = self.web_user_name_input.text().strip()
        if not username:
            return
        self._add_web_user_fn(username)
        self.web_user_name_input.clear()

    def set_web_note_users(self, users: list[dict], links_by_token: dict[str, str]) -> None:
        self._syncing_web_users = True
        try:
            self.web_users_tree.clear()
            for user in users:
                token = str(user.get("token", ""))
                item = QTreeWidgetItem(["", "", "", ""])
                self.web_users_tree.addTopLevelItem(item)
                username_input = QLineEdit(str(user.get("username", "")), self.web_users_tree)
                enabled_checkbox = QCheckBox(self.web_users_tree)
                username_input.editingFinished.connect(
                    lambda token=token, input_widget=username_input, enabled_widget=enabled_checkbox: self._update_web_user_fn(
                        token,
                        input_widget.text().strip(),
                        enabled_widget.isChecked(),
                    )
                )
                enabled_checkbox.setChecked(bool(user.get("enabled", True)))
                enabled_checkbox.toggled.connect(
                    lambda checked, token=token, input_widget=username_input: self._update_web_user_fn(
                        token,
                        input_widget.text().strip(),
                        checked,
                    )
                )
                link_input = QLineEdit(links_by_token.get(token, ""), self.web_users_tree)
                link_input.setReadOnly(True)
                copy_button = QPushButton("Copy", self.web_users_tree)
                copy_button.clicked.connect(lambda _checked=False, input_widget=link_input: self._copy_link(input_widget.text()))
                self.web_users_tree.setItemWidget(item, 0, username_input)
                self.web_users_tree.setItemWidget(item, 1, enabled_checkbox)
                self.web_users_tree.setItemWidget(item, 2, link_input)
                self.web_users_tree.setItemWidget(item, 3, copy_button)
        finally:
            self._syncing_web_users = False

    def _copy_link(self, link: str) -> None:
        mime = QMimeData()
        mime.setText(link)
        mime.setHtml(f'<a href="{link}">{link}</a>')
        QGuiApplication.clipboard().setMimeData(mime)

    def _copy_all_links(self) -> None:
        text = self._copy_all_links_fn().strip()
        if not text:
            return
        html_lines: list[str] = []
        lines = text.splitlines()
        index = 0
        while index < len(lines):
            line = lines[index]
            if not line.strip():
                html_lines.append("<br>")
                index += 1
                continue
            next_line = lines[index + 1] if index + 1 < len(lines) else ""
            if next_line.startswith("http://") or next_line.startswith("https://"):
                html_lines.append(line)
                html_lines.append(f'<a href="{next_line}">{next_line}</a>')
                index += 2
                continue
            html_lines.append(line)
            index += 1
        mime = QMimeData()
        mime.setText(text)
        mime.setHtml("<br>".join(html_lines))
        QGuiApplication.clipboard().setMimeData(mime)

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
                            note.song_time_text,
                            note.username,
                            note.note_type,
                            note.body,
                        ]
                    )
                )
            song_item.setExpanded(True)
