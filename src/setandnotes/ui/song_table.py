from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QHeaderView, QStyledItemDelegate, QTableView

from setandnotes.models.setlist_table_model import SetlistColumns, SetlistTableModel


class _ComboDelegate(QStyledItemDelegate):
    def __init__(self, choices_for_index, parent=None) -> None:
        super().__init__(parent)
        self._choices_for_index = choices_for_index

    def createEditor(self, parent, option, index):  # noqa: N802
        editor = QComboBox(parent)
        editor.setFrame(False)
        editor.setEditable(False)
        editor.setMinimumWidth(132)
        for choice in self._choices_for_index(index):
            editor.addItem(choice)
        editor.currentIndexChanged.connect(lambda _value, widget=editor: self.commitData.emit(widget))
        return editor

    def setEditorData(self, editor, index):  # noqa: N802
        current_value = index.data(Qt.DisplayRole) or ""
        choice_index = editor.findText(str(current_value))
        if choice_index >= 0:
            editor.setCurrentIndex(choice_index)

    def setModelData(self, editor, model, index):  # noqa: N802
        model.setData(index, editor.currentText(), Qt.EditRole)


class SongTable(QTableView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("setlistTable")
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.SingleSelection)
        self.setSortingEnabled(False)
        self.setTabKeyNavigation(True)
        self.setEditTriggers(
            QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed
        )
        self.setModel(SetlistTableModel())
        self.setItemDelegateForColumn(SetlistColumns.ACTIVE_VERSION, _ComboDelegate(self._version_choices_for_index, self))
        self.setItemDelegateForColumn(SetlistColumns.FPS, _ComboDelegate(lambda _index: ("25", "30"), self))
        self.model().modelReset.connect(self._refresh_version_editors)
        self.model().rowsInserted.connect(self._refresh_version_editors)
        self.model().rowsRemoved.connect(self._refresh_version_editors)
        self.model().dataChanged.connect(self._refresh_version_editors)
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(SetlistColumns.ACTIVE_VERSION, QHeaderView.ResizeToContents)
        self._refresh_version_editors()

    def _version_choices_for_index(self, index: QModelIndex) -> list[str]:
        model = self.model()
        if not isinstance(model, SetlistTableModel):
            return []

        songs = model.library().songs
        if not (0 <= index.row() < len(songs)):
            return []

        song = songs[index.row()]
        return [version.version_id for version in song.versions]

    def _refresh_version_editors(self, *args) -> None:
        self._open_version_editors()

    def _open_version_editors(self) -> None:
        model = self.model()
        if not isinstance(model, SetlistTableModel):
            return

        for row in range(model.rowCount()):
            self.openPersistentEditor(model.index(row, SetlistColumns.ACTIVE_VERSION))
