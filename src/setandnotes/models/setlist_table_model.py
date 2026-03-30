from __future__ import annotations

from enum import IntEnum

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QBrush, QColor, QFont

from setandnotes.models.library import Library
from setandnotes.models.song import Song, normalize_fps_label
from setandnotes.services.validation import validate_song


class SetlistColumns(IntEnum):
    SONG_ID = 0
    LONG_NAME = 1
    SHORT_NAME = 2
    BPM = 3
    TC_START = 4
    FPS = 5
    STATUS = 6
    ACTIVE_VERSION = 7


_HEADERS = (
    "Song ID",
    "Long Name",
    "Short Name",
    "BPM",
    "TC Hour",
    "FPS",
    "Status",
    "Version",
)

_STATUS_STYLES = {
    "ok": {"background": "#1f3a2e", "foreground": "#dff6ea"},
    "warning": {"background": "#5a4315", "foreground": "#fff0cc"},
    "error": {"background": "#5e2324", "foreground": "#ffd8d8"},
}


class SetlistTableModel(QAbstractTableModel):
    def __init__(self, library: Library | None = None) -> None:
        super().__init__()
        self._library = library or Library(project_name="")

    def set_library(self, library: Library) -> None:
        self.beginResetModel()
        self._library = library
        self.endResetModel()

    def library(self) -> Library:
        return self._library

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._library.songs)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(_HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # noqa: N802
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        if 0 <= section < len(_HEADERS):
            return _HEADERS[section]
        return None

    def flags(self, index: QModelIndex):  # noqa: N802
        if not index.isValid():
            return Qt.ItemIsEnabled

        base_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() in (
            SetlistColumns.LONG_NAME,
            SetlistColumns.SHORT_NAME,
            SetlistColumns.BPM,
            SetlistColumns.TC_START,
            SetlistColumns.FPS,
            SetlistColumns.ACTIVE_VERSION,
        ):
            return base_flags | Qt.ItemIsEditable
        return base_flags

    def _song_for_row(self, row: int) -> Song:
        return self._library.songs[row]

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # noqa: N802
        if not index.isValid():
            return None

        song = self._song_for_row(index.row())
        validation = validate_song(song, self._library.songs)
        active_version = None
        try:
            active_version = song.active_version()
        except ValueError:
            active_version = None

        if role == Qt.DisplayRole:
            column = SetlistColumns(index.column())
            if column == SetlistColumns.SONG_ID:
                return str(index.row() + 1)
            if column == SetlistColumns.LONG_NAME:
                return song.long_name
            if column == SetlistColumns.SHORT_NAME:
                return song.short_name
            if column == SetlistColumns.BPM:
                return "" if song.bpm is None else f"{song.bpm}"
            if active_version is None:
                if column == SetlistColumns.TC_START:
                    return ""
                if column == SetlistColumns.FPS:
                    return self._library.project_fps
                if column == SetlistColumns.STATUS:
                    return validation.status
                if column == SetlistColumns.ACTIVE_VERSION:
                    return ""
            if column == SetlistColumns.FPS:
                return normalize_fps_label(active_version.decoded_fps) or self._library.project_fps
            if column == SetlistColumns.TC_START:
                return active_version.decoded_tc_start or ""
            if column == SetlistColumns.STATUS:
                return validation.status
            if column == SetlistColumns.ACTIVE_VERSION:
                return active_version.version_id

        if role == Qt.TextAlignmentRole and SetlistColumns(index.column()) == SetlistColumns.STATUS:
            return int(Qt.AlignCenter)

        if role == Qt.FontRole and SetlistColumns(index.column()) == SetlistColumns.STATUS:
            font = QFont()
            font.setBold(True)
            return font

        if role in (Qt.BackgroundRole, Qt.ForegroundRole) and SetlistColumns(index.column()) == SetlistColumns.STATUS:
            palette = _STATUS_STYLES.get(validation.status, _STATUS_STYLES["warning"])
            color = palette["background"] if role == Qt.BackgroundRole else palette["foreground"]
            return QBrush(QColor(color))

        if role == Qt.ToolTipRole:
            return "; ".join(validation.messages)

        return None

    def _emit_all_rows_changed(self) -> None:
        if not self._library.songs:
            return

        top_left = self.index(0, 0)
        bottom_right = self.index(self.rowCount() - 1, self.columnCount() - 1)
        self.dataChanged.emit(top_left, bottom_right, [Qt.DisplayRole, Qt.EditRole, Qt.ToolTipRole])

    def refresh(self) -> None:
        self._emit_all_rows_changed()

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole):  # noqa: N802
        if not index.isValid() or role != Qt.EditRole:
            return False

        song = self._song_for_row(index.row())
        column = SetlistColumns(index.column())

        if column == SetlistColumns.LONG_NAME:
            text = str(value).strip()
            if not text:
                return False
            song.set_long_name(text)
        elif column == SetlistColumns.SHORT_NAME:
            text = str(value).strip()
            if not text:
                return False
            song.set_short_name(text)
        elif column == SetlistColumns.BPM:
            try:
                song.bpm = float(value)
            except (TypeError, ValueError):
                return False
        elif column == SetlistColumns.TC_START:
            try:
                version = song.active_version()
            except ValueError:
                return False
            version.decoded_tc_start = None if str(value).strip() == "" else str(value).strip()
        elif column == SetlistColumns.FPS:
            normalized = normalize_fps_label(str(value))
            if normalized not in {"25", "30"}:
                return False
            try:
                version = song.active_version()
            except ValueError:
                return False
            version.decoded_fps = normalized
        elif column == SetlistColumns.ACTIVE_VERSION:
            version_id = str(value).strip()
            if not version_id:
                return False
            try:
                song.select_active_version(version_id)
            except ValueError:
                return False
        else:
            return False

        self._emit_all_rows_changed()
        return True
