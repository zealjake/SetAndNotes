from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from setandnotes.models.library import Library
from setandnotes.models.song import Song
from setandnotes.models.version import SongVersion


def test_import_job_decodes_tc_and_saves_library(tmp_path: Path):
    from setandnotes.services.ltc_decode import LtcDecodeResult

    library_path = tmp_path / "library.json"
    library = Library(project_name="Tour Prep", library_path=str(library_path))
    library.add_song(
        Song(song_id="opening_song", long_name="Opening Song").attach_version(
            SongVersion(
                version_id="v1",
                song_id="opening_song",
                label="prep",
                source_folder="/media/v1",
                source_type="prep",
                main_audio_path="/media/v1/opening_foh.wav",
                tc_audio_path="/media/v1/opening_tc.wav",
            )
        )
    )

    import_folder = tmp_path / "Media" / "v2"
    import_folder.mkdir(parents=True)
    foh_path = import_folder / "Opening Song FOH.wav"
    tc_path = import_folder / "Opening Song TC.wav"
    foh_path.write_bytes(b"foh")
    tc_path.write_bytes(b"tc")

    from setandnotes.services.file_classify import ClassifiedMediaFile
    from setandnotes.workers.import_worker import run_import_job

    classified = [
        ClassifiedMediaFile(role="main", normalized_name="opening_song", source_name=str(foh_path)),
        ClassifiedMediaFile(role="tc", normalized_name="opening_song", source_name=str(tc_path)),
    ]
    decoded_paths: list[Path] = []

    def discover_media_files(folder: Path) -> list[Path]:
        assert folder == import_folder
        return [foh_path, tc_path]

    def classify_media_file(path: str) -> ClassifiedMediaFile:
        return next(item for item in classified if item.source_name == path)

    def decode_ltc_audio(path: Path) -> LtcDecodeResult:
        decoded_paths.append(path)
        return LtcDecodeResult(
            status="ok",
            first_timecode="01:00:00:00",
            fps="25/1",
            drop_frame=False,
            confidence=1.0,
            raw_output="decoded",
        )

    result = run_import_job(
        library=library,
        source_folder=import_folder,
        version_label="v2",
        source_type="rehearsal",
        discover_media_files=discover_media_files,
        classify_media_file=classify_media_file,
        decode_ltc_audio=decode_ltc_audio,
        save_library=lambda lib, path: Path(path).write_text(lib.to_dict().__repr__(), encoding="utf-8"),
    )

    song = result.library.song_by_id("opening_song")
    imported_version = song.versions[-1]

    assert decoded_paths == [tc_path]
    assert result.imported_files == 2
    assert song.active_version_id == "v1"
    assert imported_version.version_id == "v2"
    assert imported_version.decoded_tc_start == "01:00:00:00"
    assert imported_version.decoded_fps == "25/1"
    assert result.saved_path == str(library_path)
    assert library_path.exists()


def test_import_dialog_updates_status_text():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])

    from setandnotes.ui.import_dialog import ImportDialog

    dialog = ImportDialog()
    dialog.set_status("Import queued")

    assert app is not None
    assert dialog.status_label.text() == "Import queued"
