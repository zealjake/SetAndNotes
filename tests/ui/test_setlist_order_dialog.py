from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QAbstractItemView

from setandnotes.models.library import Library
from setandnotes.models.song import Song


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _library() -> Library:
    return Library(
        project_name="Tour Prep",
        songs=[
            Song(song_id="song-a", long_name="Alpha Song", bpm=120.0),
            Song(song_id="song-b", long_name="Beta Song", bpm=121.0),
            Song(song_id="song-c", long_name="Gamma Song", bpm=122.0),
        ],
    )


def test_setlist_order_dialog_enables_drag_drop_reordering():
    _app()

    from setandnotes.ui.setlist_order_dialog import SetlistOrderDialog

    dialog = SetlistOrderDialog(library=_library())

    assert dialog.song_table.dragDropMode() == QAbstractItemView.InternalMove
    assert dialog.song_table.dragEnabled()
    assert dialog.song_table.acceptDrops()
    assert dialog.song_table.showDropIndicator()


def test_setlist_order_dialog_reorders_library_from_table_rows():
    _app()

    from setandnotes.ui.setlist_order_dialog import SetlistOrderDialog

    library = _library()
    dialog = SetlistOrderDialog(library=library)

    dialog._move_row(0, 2)

    assert [song.long_name for song in library.songs] == ["Beta Song", "Gamma Song", "Alpha Song"]
    assert dialog.song_table.item(0, 0).text() == "1"
    assert dialog.song_table.item(2, 1).text() == "Alpha Song"
