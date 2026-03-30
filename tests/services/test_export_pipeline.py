from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from setandnotes.models.song import Song
from setandnotes.models.version import SongVersion


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _valid_song() -> Song:
    song = Song(song_id="song-1", long_name="Opening Song", bpm=128.0)
    song.attach_version(
        SongVersion(
            version_id="v2",
            song_id="song-1",
            label="v2",
            source_folder="/media/v2",
            source_type="rehearsal",
            main_audio_path="/media/v2/opening_foh.wav",
            tc_audio_path="/media/v2/opening_tc.wav",
            decoded_tc_start="01:00:00:00",
        )
    )
    return song


def _invalid_song() -> Song:
    song = Song(song_id="song-2", long_name="Broken Song", bpm=128.0)
    song.attach_version(
        SongVersion(
            version_id="v1",
            song_id="song-2",
            label="v1",
            source_folder="/media/v1",
            source_type="prep",
            main_audio_path="/media/v1/broken_foh.wav",
            tc_audio_path=None,
            decoded_tc_start=None,
        )
    )
    return song


def test_export_job_stops_before_writing_invalid_rows(tmp_path: Path):
    from setandnotes.workers.export_worker import ExportJobRequest, run_export_job

    output_dir = tmp_path / "exports"
    template_path = tmp_path / "template.rpp"
    template_path.write_text("template", encoding="utf-8")

    exported: list[str] = []

    def export_song_project(song: Song, *, template_path: Path | str, output_dir: Path | str, overwrite: bool = False) -> Path:
        exported.append(song.song_id)
        target = Path(output_dir) / song.long_name / f"{song.long_name}.rpp"
        target.write_text("exported", encoding="utf-8")
        return target

    result = run_export_job(
        ExportJobRequest(
            songs=[_valid_song(), _invalid_song()],
            output_dir=output_dir,
            template_path=template_path,
        ),
        export_song_project=export_song_project,
        path_exists=lambda _: False,
    )

    assert result.status == "error"
    assert result.exported_paths == []
    assert result.invalid_songs == ["Broken Song"]
    assert exported == []


def test_export_job_requires_confirmation_before_overwrite(tmp_path: Path):
    from setandnotes.workers.export_worker import ExportJobRequest, run_export_job

    output_dir = tmp_path / "exports"
    template_path = tmp_path / "template.rpp"
    template_path.write_text("template", encoding="utf-8")

    song = _valid_song()
    expected_output = output_dir / "Opening Song" / "Opening Song.rpp"

    result = run_export_job(
        ExportJobRequest(
            songs=[song],
            output_dir=output_dir,
            template_path=template_path,
        ),
        path_exists=lambda path: path == expected_output,
    )

    assert result.status == "needs_confirmation"
    assert result.overwrite_targets == [expected_output]
    assert result.exported_paths == []


def test_export_job_blocks_existing_project_with_different_song_project_id(tmp_path: Path):
    from setandnotes.workers.export_worker import ExportJobRequest, run_export_job

    output_dir = tmp_path / "exports"
    template_path = tmp_path / "template.rpp"
    template_path.write_text("template", encoding="utf-8")

    song = _valid_song()
    expected_output = output_dir / "Opening Song" / "Opening Song.rpp"
    expected_output.parent.mkdir(parents=True, exist_ok=True)
    expected_output.write_text("legacy", encoding="utf-8")

    result = run_export_job(
        ExportJobRequest(
            songs=[song],
            output_dir=output_dir,
            template_path=template_path,
        ),
        path_exists=lambda path: path == expected_output,
        read_song_project_id_fn=lambda path: "different-song-project-id",
    )

    assert result.status == "error"
    assert result.invalid_songs == ["Opening Song"]
    assert "different song project id" in result.warnings[0].lower()
    assert result.overwrite_targets == []


def test_export_dialog_summarizes_and_retries_overwrite(tmp_path: Path):
    _app()

    from setandnotes.workers.export_worker import ExportJobRequest, ExportJobResult
    from setandnotes.ui.export_dialog import ExportDialog

    song = _valid_song()
    output_dir = tmp_path / "exports"
    template_path = tmp_path / "template.rpp"
    template_path.write_text("template", encoding="utf-8")

    calls: list[bool] = []

    def run_export_job(request: ExportJobRequest, **kwargs):
        calls.append(request.overwrite)
        if not request.overwrite:
            return ExportJobResult(
                status="needs_confirmation",
                exported_paths=[],
                invalid_songs=[],
                overwrite_targets=[output_dir / "Opening Song" / "Opening Song.rpp"],
                warnings=[],
            )
        return ExportJobResult(
            status="ok",
            exported_paths=[output_dir / "Opening Song" / "Opening Song.rpp"],
            invalid_songs=[],
            overwrite_targets=[],
            warnings=[],
        )

    dialog = ExportDialog(
        songs=[song],
        output_dir=output_dir,
        template_path=template_path,
        run_export_job=run_export_job,
        confirm_overwrite=lambda paths: True,
    )

    assert "1 song selected" in dialog.summary_label.text().lower()
    assert str(output_dir) in dialog.summary_label.text()

    dialog.run_export()

    assert calls == [False, True]
    assert "exported 1 project" in dialog.status_label.text().lower()
    assert str(output_dir) in dialog.status_label.text()


def test_export_dialog_shows_validation_reasons_when_blocked(tmp_path: Path):
    _app()

    from setandnotes.workers.export_worker import ExportJobRequest, ExportJobResult
    from setandnotes.ui.export_dialog import ExportDialog

    song = _invalid_song()
    output_dir = tmp_path / "exports"
    template_path = tmp_path / "template.rpp"
    template_path.write_text("template", encoding="utf-8")

    def run_export_job(request: ExportJobRequest, **kwargs):
        return ExportJobResult(
            status="error",
            exported_paths=[],
            invalid_songs=["Broken Song"],
            overwrite_targets=[],
            warnings=["Broken Song: missing tc audio path; missing decoded tc start"],
        )

    dialog = ExportDialog(
        songs=[song],
        output_dir=output_dir,
        template_path=template_path,
        run_export_job=run_export_job,
    )

    dialog.run_export()

    assert "export blocked" in dialog.status_label.text().lower()
    assert "missing tc audio path" in dialog.status_label.text().lower()
