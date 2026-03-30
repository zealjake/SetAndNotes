from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from setandnotes.models.song import Song
from setandnotes.ui.tc_waveform_view import TcWaveformView


def _format_tc_entry_offset(seconds: float | None, fps: float) -> str:
    if seconds is None:
        return ""

    total_frames = max(0, int(round(seconds * fps)))
    frames = total_frames % int(round(fps))
    total_seconds = total_frames // int(round(fps))
    whole_seconds = total_seconds % 60
    total_minutes = total_seconds // 60
    minutes = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}:{frames:02d}"


def _parse_tc_entry_offset(text: str, fps: float) -> float | None:
    value = text.strip()
    if not value:
        return None

    try:
        return max(0.0, float(value))
    except ValueError:
        pass

    parts = value.split(":")
    if len(parts) != 4:
        raise ValueError(f"unsupported tc entry offset: {value}")
    hours, minutes, seconds, frames = (int(part) for part in parts)
    return max(0.0, ((hours * 60 + minutes) * 60 + seconds) + (frames / fps))


class DetailPanel(QWidget):
    songUpdated = Signal(object)
    rebuildRequested = Signal(object)

    def __init__(self, parent=None, *, audio_path_picker: Callable[[str | None], str | None] | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("detailPanel")

        self._song: Song | None = None
        self._audio_path_picker = audio_path_picker

        self.song_title_label = QLabel("No song selected")
        self.song_title_label.setObjectName("detailTitle")
        self.version_status_label = QLabel("Select a row to inspect version details.")
        self.version_status_label.setObjectName("detailStatus")
        self.active_version_value_label = QLabel("-", self)
        self.active_version_value_label.setObjectName("activeVersionValue")

        self.main_audio_input = QLineEdit(self)
        self.main_audio_input.setObjectName("mainAudioInput")
        self.main_audio_input.editingFinished.connect(self._apply_main_audio_text)
        self.main_audio_browse_button = QPushButton("Browse", self)
        self.main_audio_browse_button.setObjectName("mainAudioBrowseButton")
        self.main_audio_browse_button.clicked.connect(self._browse_main_audio)

        self.tc_audio_input = QLineEdit(self)
        self.tc_audio_input.setObjectName("tcAudioInput")
        self.tc_audio_input.editingFinished.connect(self._apply_tc_audio_text)
        self.tc_audio_browse_button = QPushButton("Browse", self)
        self.tc_audio_browse_button.setObjectName("tcAudioBrowseButton")
        self.tc_audio_browse_button.clicked.connect(self._browse_tc_audio)

        self.tc_entry_offset_input = QLineEdit(self)
        self.tc_entry_offset_input.setObjectName("tcEntryOffsetInput")
        self.tc_entry_offset_input.setPlaceholderText("00:00:23:00 or seconds")
        self.tc_entry_offset_input.editingFinished.connect(self._apply_tc_entry_offset_text)

        self.tc_waveform_view = TcWaveformView(self)
        self.tc_waveform_view.markerChanged.connect(self._apply_tc_entry_offset_from_waveform)

        self.multicam_video_input = QLineEdit(self)
        self.multicam_video_input.setObjectName("multicamVideoInput")
        self.multicam_video_input.setReadOnly(True)

        self.wideshot_1080_input = QLineEdit(self)
        self.wideshot_1080_input.setObjectName("wideshot1080Input")
        self.wideshot_1080_input.setReadOnly(True)

        self.rebuild_project_button = QPushButton("Rebuild Project", self)
        self.rebuild_project_button.setObjectName("rebuildProjectButton")
        self.rebuild_project_button.clicked.connect(self._emit_rebuild_request)

        main_audio_row = QWidget(self)
        main_audio_layout = QHBoxLayout(main_audio_row)
        main_audio_layout.setContentsMargins(0, 0, 0, 0)
        main_audio_layout.addWidget(self.main_audio_input)
        main_audio_layout.addWidget(self.main_audio_browse_button)

        tc_audio_row = QWidget(self)
        tc_audio_layout = QHBoxLayout(tc_audio_row)
        tc_audio_layout.setContentsMargins(0, 0, 0, 0)
        tc_audio_layout.addWidget(self.tc_audio_input)
        tc_audio_layout.addWidget(self.tc_audio_browse_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.song_title_label)
        layout.addWidget(self.version_status_label)

        form = QFormLayout()
        form.addRow("Version", self.active_version_value_label)
        form.addRow("Main Audio", main_audio_row)
        form.addRow("TC Audio", tc_audio_row)
        form.addRow("TC Entry", self.tc_entry_offset_input)
        form.addRow("Multicam", self.multicam_video_input)
        form.addRow("WideShot1080", self.wideshot_1080_input)
        layout.addLayout(form)
        layout.addWidget(self.tc_waveform_view)
        layout.addWidget(self.rebuild_project_button)

        self._set_enabled(False)

    def _set_enabled(self, enabled: bool) -> None:
        self.main_audio_input.setEnabled(enabled)
        self.main_audio_browse_button.setEnabled(enabled)
        self.tc_audio_input.setEnabled(enabled)
        self.tc_audio_browse_button.setEnabled(enabled)
        self.tc_entry_offset_input.setEnabled(enabled)
        self.tc_waveform_view.setEnabled(enabled)
        self.rebuild_project_button.setEnabled(enabled)

    def set_song(self, song: Song | None) -> None:
        self._song = song

        if song is None:
            self.song_title_label.setText("No song selected")
            self.version_status_label.setText("Select a row to inspect version details.")
            self.active_version_value_label.setText("-")
            self.main_audio_input.clear()
            self.tc_audio_input.clear()
            self.tc_entry_offset_input.clear()
            self.multicam_video_input.clear()
            self.wideshot_1080_input.clear()
            self.tc_waveform_view.set_audio_path(None)
            self.tc_waveform_view.set_marker_seconds(None)
            self._set_enabled(False)
            return

        self.song_title_label.setText(song.long_name)
        self._set_enabled(bool(song.versions))
        self._refresh_status()

    def current_song(self) -> Song | None:
        return self._song

    def _refresh_status(self) -> None:
        song = self._song
        if song is None:
            return

        try:
            active_version = song.active_version()
        except ValueError:
            self.version_status_label.setText("No active version selected")
            self.active_version_value_label.setText("-")
            self.main_audio_input.clear()
            self.tc_audio_input.clear()
            self.tc_entry_offset_input.clear()
            self.multicam_video_input.clear()
            self.wideshot_1080_input.clear()
            self.tc_waveform_view.set_audio_path(None)
            self.tc_waveform_view.set_marker_seconds(None)
            return

        self.active_version_value_label.setText(active_version.version_id)
        self.main_audio_input.setText(active_version.main_audio_path or "")
        self.tc_audio_input.setText(active_version.tc_audio_path or "")
        self.tc_entry_offset_input.setText(_format_tc_entry_offset(active_version.tc_entry_offset_seconds, self._fps_value()))
        self.multicam_video_input.setText(active_version.video_assets.get("Multicam", ""))
        self.wideshot_1080_input.setText(active_version.video_assets.get("WideShot1080", ""))
        self.tc_waveform_view.set_audio_path(active_version.tc_audio_path)
        self.tc_waveform_view.set_marker_seconds(active_version.tc_entry_offset_seconds)

        latest_version = song.versions[-1] if song.versions else None
        if latest_version is not None and latest_version.version_id != active_version.version_id:
            self.version_status_label.setText(
                f"Active version: {active_version.version_id} | Newer imported version: {latest_version.version_id}"
            )
        else:
            self.version_status_label.setText(f"Active version: {active_version.version_id}")

    def _apply_main_audio_text(self) -> None:
        song = self._song
        if song is None:
            return

        try:
            version = song.active_version()
        except ValueError:
            return

        version.main_audio_path = self.main_audio_input.text().strip() or None
        self.songUpdated.emit(song)

    def _apply_tc_audio_text(self) -> None:
        song = self._song
        if song is None:
            return

        try:
            version = song.active_version()
        except ValueError:
            return

        version.tc_audio_path = self.tc_audio_input.text().strip() or None
        self.tc_waveform_view.set_audio_path(version.tc_audio_path)
        self.songUpdated.emit(song)

    def _apply_tc_entry_offset_text(self) -> None:
        song = self._song
        if song is None:
            return

        try:
            version = song.active_version()
        except ValueError:
            return

        try:
            offset = _parse_tc_entry_offset(self.tc_entry_offset_input.text(), self._fps_value())
        except (ValueError, TypeError):
            self.tc_entry_offset_input.setText(_format_tc_entry_offset(version.tc_entry_offset_seconds, self._fps_value()))
            return

        version.tc_entry_offset_seconds = offset
        self.tc_waveform_view.set_marker_seconds(offset)
        self.tc_entry_offset_input.setText(_format_tc_entry_offset(offset, self._fps_value()))
        self.songUpdated.emit(song)

    def _apply_tc_entry_offset_from_waveform(self, seconds: float) -> None:
        song = self._song
        if song is None:
            return

        try:
            version = song.active_version()
        except ValueError:
            return

        version.tc_entry_offset_seconds = max(0.0, float(seconds))
        self.tc_entry_offset_input.setText(_format_tc_entry_offset(version.tc_entry_offset_seconds, self._fps_value()))
        self.songUpdated.emit(song)

    def _browse_main_audio(self) -> None:
        self._browse_audio("main")

    def _browse_tc_audio(self) -> None:
        self._browse_audio("tc")

    def _browse_audio(self, role: str) -> None:
        if self._audio_path_picker is None or self._song is None:
            return

        try:
            version = self._song.active_version()
        except ValueError:
            return

        current_path = version.main_audio_path if role == "main" else version.tc_audio_path
        selected_path = self._audio_path_picker(current_path)
        if not selected_path:
            return

        if role == "main":
            version.main_audio_path = selected_path
            self.main_audio_input.setText(selected_path)
        else:
            version.tc_audio_path = selected_path
            self.tc_audio_input.setText(selected_path)
            self.tc_waveform_view.set_audio_path(selected_path)
        self.songUpdated.emit(self._song)

    def _fps_value(self) -> float:
        song = self._song
        if song is None:
            return 25.0
        try:
            version = song.active_version()
        except ValueError:
            return 25.0

        raw_value = (version.decoded_fps or "").strip()
        if raw_value == "30":
            return 30.0
        return 25.0

    def _emit_rebuild_request(self) -> None:
        if self._song is None:
            return
        self.rebuildRequested.emit(self._song)
