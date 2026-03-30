from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem, QVBoxLayout

from setandnotes.models.library import Library


class _SetlistOrderTable(QTableWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._dialog = None

    def set_dialog(self, dialog: "SetlistOrderDialog") -> None:
        self._dialog = dialog

    def dropEvent(self, event) -> None:  # noqa: N802
        if self._dialog is None:
            super().dropEvent(event)
            return

        source_row = self.currentRow()
        if source_row < 0:
            event.ignore()
            return

        target_row = self._dialog._target_row_for_drop(self, event.position().toPoint())
        self._dialog._move_row(source_row, target_row)
        event.acceptProposedAction()


class SetlistOrderDialog(QDialog):
    def __init__(self, parent=None, *, library: Library) -> None:
        super().__init__(parent)
        self.setObjectName("setlistOrderDialog")
        self.setWindowTitle("Setlist Order")
        self.resize(640, 420)
        self._library = library

        self.song_table = _SetlistOrderTable(self)
        self.song_table.set_dialog(self)
        self.song_table.setObjectName("setlistOrderTable")
        self.song_table.setColumnCount(2)
        self.song_table.setHorizontalHeaderLabels(["Song ID", "Long Name"])
        self.song_table.verticalHeader().setVisible(False)
        self.song_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.song_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.song_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.song_table.setDragDropMode(QAbstractItemView.InternalMove)
        self.song_table.setDragEnabled(True)
        self.song_table.setAcceptDrops(True)
        self.song_table.setDropIndicatorShown(True)
        self.song_table.setDefaultDropAction(Qt.MoveAction)
        self.song_table.setDragDropOverwriteMode(False)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.song_table)
        layout.addWidget(buttons)

        self._reload_rows()

    def _reload_rows(self) -> None:
        self.song_table.setRowCount(len(self._library.songs))
        for row, song in enumerate(self._library.songs):
            order_item = QTableWidgetItem(str(row + 1))
            order_item.setTextAlignment(Qt.AlignCenter)
            order_item.setData(Qt.UserRole, song.song_id)
            name_item = QTableWidgetItem(song.long_name)
            name_item.setData(Qt.UserRole, song.song_id)
            self.song_table.setItem(row, 0, order_item)
            self.song_table.setItem(row, 1, name_item)
        if self._library.songs and self.song_table.currentRow() < 0:
            self.song_table.selectRow(0)

    def _target_row_for_drop(self, table: QTableWidget, point) -> int:
        target_index = table.indexAt(point)
        if not target_index.isValid():
            return table.rowCount() - 1

        row = target_index.row()
        if table.dropIndicatorPosition() == QAbstractItemView.BelowItem:
            return min(table.rowCount() - 1, row + 1)
        return row

    def _move_row(self, source_row: int, target_row: int) -> None:
        if source_row == target_row or not (0 <= source_row < self.song_table.rowCount()):
            return
        if not (0 <= target_row < self.song_table.rowCount()):
            return

        moved_song = self._library.songs.pop(source_row)
        self._library.songs.insert(target_row, moved_song)
        self._reload_rows()
        self.song_table.selectRow(target_row)
