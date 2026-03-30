from __future__ import annotations

import os
import struct
import wave
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from setandnotes.models.song import Song
from setandnotes.models.version import SongVersion


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _song_with_versions() -> Song:
    song = Song(song_id="song-1", long_name="Opening Song", bpm=128.0)
    song.attach_version(
        SongVersion(
            version_id="v1",
            song_id="song-1",
            label="prep",
            source_folder="/media/v1",
            source_type="prep",
            main_audio_path="/media/v1/opening_foh.wav",
            tc_audio_path="/media/v1/opening_tc.wav",
            decoded_tc_start="01:00:00:00",
        )
    )
    song.attach_version(
        SongVersion(
            version_id="v2",
            song_id="song-1",
            label="rehearsal-1",
            source_folder="/media/v2",
            source_type="rehearsal",
            main_audio_path="/media/v2/opening_foh.wav",
            tc_audio_path="/media/v2/opening_tc.wav",
            decoded_tc_start="01:10:00:00",
        )
    )
    song.attach_version(
        SongVersion(
            version_id="v3",
            song_id="song-1",
            label="rehearsal-2",
            source_folder="/media/v3",
            source_type="rehearsal",
            main_audio_path="/media/v3/opening_foh.wav",
            tc_audio_path="/media/v3/opening_tc.wav",
            decoded_tc_start="01:20:00:00",
        )
    )
    song.select_active_version("v1")
    return song


def _write_tc_wav(path: Path, *, frames: int = 1000) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(1000)
        samples = bytearray()
        for index in range(frames):
            amplitude = int(16000 * (((index // 50) % 2) * 2 - 1))
            samples.extend(struct.pack("<h", amplitude))
        handle.writeframes(bytes(samples))
    return path


def test_detail_panel_shows_active_version_and_audio_paths():
    _app()

    from setandnotes.ui.detail_panel import DetailPanel

    song = _song_with_versions()
    panel = DetailPanel()
    panel.set_song(song)

    assert panel.song_title_label.text() == "Opening Song"
    assert panel.active_version_value_label.text() == "v1"
    assert panel.main_audio_input.text() == "/media/v1/opening_foh.wav"
    assert panel.tc_audio_input.text() == "/media/v1/opening_tc.wav"
    assert panel.multicam_video_input.text() == ""
    assert panel.wideshot_1080_input.text() == ""
    assert panel.tc_entry_offset_input.text() == ""
    assert "newer imported version" in panel.version_status_label.text().lower()


def test_detail_panel_shows_active_version_video_assets():
    _app()

    from setandnotes.ui.detail_panel import DetailPanel

    song = _song_with_versions()
    active_version = song.active_version()
    active_version.video_assets["Multicam"] = "/video/opening_multicam.mov"
    active_version.video_assets["WideShot1080"] = "/video/opening_wideshot1080.mov"

    panel = DetailPanel()
    panel.set_song(song)

    assert panel.multicam_video_input.text() == "/video/opening_multicam.mov"
    assert panel.wideshot_1080_input.text() == "/video/opening_wideshot1080.mov"


def test_detail_panel_emits_rebuild_request_separately_from_version_selection():
    _app()

    from setandnotes.ui.detail_panel import DetailPanel

    song = _song_with_versions()
    panel = DetailPanel()
    panel.set_song(song)

    emitted: list[str] = []
    panel.rebuildRequested.connect(lambda value: emitted.append(value.song_id))

    panel.rebuild_project_button.click()

    assert emitted == ["song-1"]
    assert song.active_version_id == "v1"


def test_detail_panel_audio_browse_buttons_update_active_version_paths(tmp_path: Path):
    _app()

    from setandnotes.ui.detail_panel import DetailPanel

    song = _song_with_versions()
    picked_paths = iter(
        [
            str(tmp_path / "replacement_main.wav"),
            str(tmp_path / "replacement_tc.wav"),
        ]
    )

    panel = DetailPanel(audio_path_picker=lambda _current: next(picked_paths))
    panel.set_song(song)

    panel.main_audio_browse_button.click()
    panel.tc_audio_browse_button.click()

    assert song.active_version().main_audio_path == str(tmp_path / "replacement_main.wav")
    assert song.active_version().tc_audio_path == str(tmp_path / "replacement_tc.wav")
    assert panel.main_audio_input.text() == str(tmp_path / "replacement_main.wav")
    assert panel.tc_audio_input.text() == str(tmp_path / "replacement_tc.wav")


def test_detail_panel_shows_saved_tc_entry_offset(tmp_path: Path):
    _app()

    from setandnotes.ui.detail_panel import DetailPanel

    song = _song_with_versions()
    tc_path = _write_tc_wav(tmp_path / "tc.wav", frames=30000)
    active_version = song.active_version()
    active_version.tc_audio_path = str(tc_path)
    active_version.tc_entry_offset_seconds = 23.0

    panel = DetailPanel()
    panel.resize(360, 320)
    panel.set_song(song)

    assert panel.tc_entry_offset_input.text() == "00:00:23:00"
    assert abs(panel.tc_waveform_view.marker_seconds - 23.0) < 0.05


def test_detail_panel_waveform_click_updates_tc_entry_offset(tmp_path: Path):
    _app()

    from setandnotes.ui.detail_panel import DetailPanel

    song = _song_with_versions()
    tc_path = _write_tc_wav(tmp_path / "tc.wav", frames=1000)
    active_version = song.active_version()
    active_version.tc_audio_path = str(tc_path)

    panel = DetailPanel()
    panel.resize(420, 320)
    panel.set_song(song)
    panel.show()
    panel.tc_waveform_view.resize(200, 80)
    panel.tc_waveform_view.show()
    _app().processEvents()

    click_x = int(panel.tc_waveform_view.width() * 0.25)
    QTest.mouseClick(panel.tc_waveform_view, Qt.LeftButton, pos=QPoint(click_x, 40))

    assert active_version.tc_entry_offset_seconds is not None
    assert abs(active_version.tc_entry_offset_seconds - 0.25) < 0.08
    assert panel.tc_entry_offset_input.text().startswith("00:00:00:")
