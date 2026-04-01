from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication, QCheckBox, QLineEdit, QPushButton

from setandnotes.models.rehearsal_notes import RehearsalNote, SongNoteSection


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_notes_page_captures_timestamp_on_button_press_and_creates_note_from_popup():
    _app()

    created: list[tuple[str, str, str, float]] = []

    from setandnotes.ui.notes_page import NotesPage

    page = NotesPage(
        capture_timestamp_fn=lambda: 23.5,
        create_note_fn=lambda u, t, b, ts: created.append((u, t, b, ts)) or {"marker_name": "ok"},
    )
    page.username_input.setText("Jake")

    page._start_note_capture("Content")
    assert page.pending_timestamp == 23.5
    assert page.note_dialog is not None
    assert page.note_dialog.windowTitle() == "Add Content Note"

    page.note_dialog.note_body_input.setPlainText("Wrong lyric layer")
    page._confirm_note_dialog()

    assert created == [("Jake", "Content", "Wrong lyric layer", 23.5)]
    assert page.username_input.text() == "Jake"
    assert page.pending_timestamp is None
    assert page.status_label.text() == "Note added to REAPER"


def test_notes_page_shows_error_status_when_timestamp_capture_fails():
    _app()

    from setandnotes.ui.notes_page import NotesPage

    page = NotesPage(capture_timestamp_fn=lambda: (_ for _ in ()).throw(RuntimeError("REAPER unavailable")))
    page.username_input.setText("Jake")

    page._start_note_capture("General")

    assert page.status_label.text() == "REAPER unavailable"
    assert page.note_dialog is None


def test_notes_page_keeps_popup_open_when_create_note_fails():
    _app()

    from setandnotes.ui.notes_page import NotesPage

    page = NotesPage(
        capture_timestamp_fn=lambda: 11.0,
        create_note_fn=lambda u, t, b, ts: (_ for _ in ()).throw(RuntimeError("Marker create failed")),
    )
    page.username_input.setText("Jake")

    page._start_note_capture("Cameras")
    page.note_dialog.note_body_input.setPlainText("Test note")
    page._confirm_note_dialog()

    assert page.status_label.text() == "Marker create failed"
    assert page.note_dialog is not None
    assert page.pending_timestamp == 11.0


def test_notes_page_renders_grouped_song_headers_and_notes():
    _app()

    from setandnotes.ui.notes_page import NotesPage

    page = NotesPage(capture_timestamp_fn=lambda: 0.0, create_note_fn=lambda u, t, b, ts: {"marker_name": "ok"})
    page.set_note_sections(
        [
            SongNoteSection(
                song_name="Intro Song",
                song_marker_guid="song-1",
                notes=[
                    RehearsalNote(
                        guid="note-1",
                        time_text="00:01:07.125",
                        song_time_text="00:00:07:03",
                        username="Jake",
                        note_type="Cameras",
                        body="Push in too slow",
                    )
                ],
            )
        ]
    )

    assert page.notes_tree.topLevelItemCount() == 1
    song_item = page.notes_tree.topLevelItem(0)
    assert song_item.text(0) == "Intro Song"
    assert song_item.childCount() == 1
    assert song_item.child(0).text(0) == "00:01:07.125"
    assert song_item.child(0).text(1) == "00:00:07:03"
    assert song_item.child(0).text(2) == "Jake"
    assert song_item.child(0).text(3) == "Cameras"
    assert song_item.child(0).text(4) == "Push in too slow"


def test_notes_page_adds_and_edits_project_web_note_users():
    _app()

    added: list[str] = []
    updated: list[tuple[str, str, bool]] = []

    from setandnotes.ui.notes_page import NotesPage

    page = NotesPage(
        add_web_user_fn=lambda username: added.append(username),
        update_web_user_fn=lambda token, username, enabled: updated.append((token, username, enabled)),
    )

    page.web_user_name_input.setText("CreativeDirector")
    page.add_web_user_button.click()

    assert added == ["CreativeDirector"]
    assert page.web_user_name_input.text() == ""

    page.set_web_note_users(
        [{"username": "CreativeDirector", "token": "tok-creative", "slug": "creative-director", "enabled": True}],
        {"tok-creative": "http://192.168.1.50:8787/notes/u/creative-director"},
    )

    assert page.web_users_tree.topLevelItemCount() == 1
    item = page.web_users_tree.topLevelItem(0)
    username_input = page.web_users_tree.itemWidget(item, 0)
    enabled_checkbox = page.web_users_tree.itemWidget(item, 1)
    link_input = page.web_users_tree.itemWidget(item, 2)
    copy_button = page.web_users_tree.itemWidget(item, 3)

    assert isinstance(username_input, QLineEdit)
    assert isinstance(enabled_checkbox, QCheckBox)
    assert isinstance(link_input, QLineEdit)
    assert isinstance(copy_button, QPushButton)
    assert username_input.text() == "CreativeDirector"
    assert link_input.text() == "http://192.168.1.50:8787/notes/u/creative-director"
    assert link_input.isReadOnly()

    username_input.setText("CreativeLead")
    username_input.editingFinished.emit()
    assert updated[-1] == ("tok-creative", "CreativeLead", True)

    enabled_checkbox.setChecked(False)
    assert updated[-1] == ("tok-creative", "CreativeLead", False)

    QApplication.clipboard().clear()
    copy_button.click()
    assert QApplication.clipboard().text() == "http://192.168.1.50:8787/notes/u/creative-director"


def test_notes_page_can_copy_all_links_as_message():
    _app()

    copied: list[str] = []

    from setandnotes.ui.notes_page import NotesPage

    page = NotesPage(copy_all_links_fn=lambda: "USER 1 : http://host/one\nUSER 2 : http://host/two")
    page.copy_all_web_users_button.click()

    mime = QApplication.clipboard().mimeData()
    assert QApplication.clipboard().text() == "USER 1 : http://host/one\nUSER 2 : http://host/two"
    assert mime is not None
    assert mime.hasHtml()
