from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QAbstractItemView, QComboBox, QHeaderView, QMainWindow, QTableView, QWidget, QToolBar


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_exposes_expected_shell():
    _app()

    from setandnotes.main_window import SetAndNotesMainWindow

    window = SetAndNotesMainWindow()

    assert isinstance(window, QMainWindow)
    assert window.windowTitle() == "SetAndNotes"
    assert window.findChild(QTableView, "setlistTable") is not None
    assert window.findChild(QWidget, "detailPanel") is not None
    assert window.findChild(QWidget, "statusPanel") is not None

    project_toolbar = window.findChild(QToolBar, "projectToolbar")
    workflow_toolbar = window.findChild(QToolBar, "workflowToolbar")
    assert project_toolbar is not None
    assert workflow_toolbar is not None
    assert [action.text() for action in project_toolbar.actions() if action.text()] == [
        "New Project",
        "Open Project",
        "Save Project",
        "Save Project As",
        "Close Project",
    ]
    assert window.findChild(QComboBox, "projectFpsCombo") is not None
    assert [action.text() for action in workflow_toolbar.actions()] == [
        "Import Folder",
        "Import TD Render Folder",
        "Set RPP Template",
        "Generate Projects",
    ]


def test_theme_and_font_hooks_exist():
    _app()

    from setandnotes.styles.fonts import activate_application_fonts, preferred_font_families
    from setandnotes.styles.theme import application_stylesheet

    families = preferred_font_families()
    stylesheet = application_stylesheet()

    assert "Aktiv Grotesk" in families
    assert "Aktiv Grotesk Ex" in families
    assert "QMainWindow" in stylesheet
    assert "QTableView::item:selected" in stylesheet
    assert "QTableView::item:hover" in stylesheet
    assert "alternate-background-color" in stylesheet

    loaded = activate_application_fonts(QApplication.instance())
    assert isinstance(loaded, dict)


def test_song_table_is_tuned_for_fast_editing():
    _app()

    from setandnotes.main_window import SetAndNotesMainWindow
    from setandnotes.models.setlist_table_model import SetlistColumns

    window = SetAndNotesMainWindow()
    table = window.song_table

    assert table.tabKeyNavigation()
    assert table.editTriggers() & QAbstractItemView.SelectedClicked
    assert table.editTriggers() & QAbstractItemView.EditKeyPressed
    assert table.editTriggers() & QAbstractItemView.AnyKeyPressed
    for column in range(table.model().columnCount()):
        if column == SetlistColumns.ACTIVE_VERSION:
            assert table.horizontalHeader().sectionResizeMode(column) == QHeaderView.ResizeToContents
        else:
            assert table.horizontalHeader().sectionResizeMode(column) == QHeaderView.Stretch
    assert table.selectionBehavior() == QTableView.SelectRows


def test_song_table_keeps_version_editors_visible():
    _app()

    from setandnotes.models.library import Library
    from setandnotes.models.song import Song
    from setandnotes.models.version import SongVersion
    from setandnotes.models.setlist_table_model import SetlistColumns
    from setandnotes.ui.song_table import SongTable

    song = Song(song_id="song-1", long_name="Opening Song", bpm=128.0)
    song.attach_version(
        SongVersion(
            version_id="v1",
            song_id="song-1",
            label="prep",
            source_folder="/media/v1",
            source_type="prep",
        )
    )
    song.attach_version(
        SongVersion(
            version_id="v2",
            song_id="song-1",
            label="rehearsal",
            source_folder="/media/v2",
            source_type="rehearsal",
        )
    )

    table = SongTable()
    table.model().set_library(Library(project_name="Tour Prep", songs=[song]))

    assert table.isPersistentEditorOpen(table.model().index(0, SetlistColumns.ACTIVE_VERSION))
