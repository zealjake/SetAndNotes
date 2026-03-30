from __future__ import annotations

import struct
import wave
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class TcWaveformView(QWidget):
    markerChanged = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("tcWaveformView")
        self.setMinimumHeight(80)
        self._peaks: list[float] = []
        self.duration_seconds = 0.0
        self.marker_seconds: float | None = None
        self._audio_path: str | None = None

    def set_audio_path(self, path: str | None) -> None:
        if path == self._audio_path:
            self.update()
            return

        self._audio_path = path
        self._peaks = []
        self.duration_seconds = 0.0
        if path:
            try:
                self._peaks, self.duration_seconds = _load_waveform_preview(Path(path))
            except (FileNotFoundError, ValueError, wave.Error, OSError, struct.error):
                self._peaks = []
                self.duration_seconds = 0.0
        self.update()

    def set_marker_seconds(self, seconds: float | None) -> None:
        if seconds is None or self.duration_seconds <= 0:
            self.marker_seconds = seconds
        else:
            self.marker_seconds = max(0.0, min(float(seconds), self.duration_seconds))
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton or self.duration_seconds <= 0 or self.width() <= 0:
            super().mousePressEvent(event)
            return

        ratio = max(0.0, min(1.0, event.position().x() / max(1.0, float(self.width()))))
        marker_seconds = ratio * self.duration_seconds
        self.set_marker_seconds(marker_seconds)
        self.markerChanged.emit(marker_seconds)
        event.accept()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        painter.fillRect(self.rect(), QColor("#121717"))

        center_y = self.height() / 2.0
        baseline_pen = QPen(QColor("#3c4747"))
        baseline_pen.setWidth(1)
        painter.setPen(baseline_pen)
        painter.drawLine(0, int(center_y), self.width(), int(center_y))

        if self._peaks:
            waveform_pen = QPen(QColor("#c7ddd5"))
            waveform_pen.setWidth(1)
            painter.setPen(waveform_pen)
            step = self.width() / max(1, len(self._peaks))
            half_height = max(1.0, (self.height() - 12) / 2.0)
            for index, peak in enumerate(self._peaks):
                x = step * index + (step / 2.0)
                amplitude = peak * half_height
                painter.drawLine(QPointF(x, center_y - amplitude), QPointF(x, center_y + amplitude))

        if self.marker_seconds is not None and self.duration_seconds > 0:
            marker_x = (self.marker_seconds / self.duration_seconds) * self.width()
            marker_pen = QPen(QColor("#e8cf70"))
            marker_pen.setWidth(2)
            painter.setPen(marker_pen)
            painter.drawLine(int(marker_x), 0, int(marker_x), self.height())

        painter.end()


def _load_waveform_preview(path: Path, bins: int = 256) -> tuple[list[float], float]:
    with wave.open(str(path), "rb") as handle:
        frame_count = handle.getnframes()
        sample_rate = handle.getframerate()
        channel_count = handle.getnchannels()
        sample_width = handle.getsampwidth()
        raw_frames = handle.readframes(frame_count)

    if frame_count <= 0 or sample_rate <= 0:
        return [], 0.0

    samples = _decode_samples(raw_frames, sample_width)
    frames: list[float] = []
    stride = max(1, channel_count)
    for index in range(0, len(samples), stride):
        window = samples[index : index + stride]
        frames.append(sum(abs(sample) for sample in window) / len(window))

    if not frames:
        return [], frame_count / sample_rate

    max_value = max(frames) or 1.0
    bucket_size = max(1, len(frames) // bins)
    peaks: list[float] = []
    for start in range(0, len(frames), bucket_size):
        bucket = frames[start : start + bucket_size]
        peaks.append(max(bucket) / max_value)

    return peaks, frame_count / sample_rate


def _decode_samples(raw_frames: bytes, sample_width: int) -> list[int]:
    if sample_width == 1:
        return [sample - 128 for sample in raw_frames]
    if sample_width == 2:
        count = len(raw_frames) // 2
        return list(struct.unpack(f"<{count}h", raw_frames))
    if sample_width == 4:
        count = len(raw_frames) // 4
        return list(struct.unpack(f"<{count}i", raw_frames))
    raise ValueError(f"unsupported WAV sample width: {sample_width}")
