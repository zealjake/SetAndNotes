from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QMessageBox, QPushButton, QVBoxLayout

from setandnotes.models.song import Song
from setandnotes.workers.export_worker import ExportJobRequest, ExportJobResult, run_export_job


def _default_confirm_overwrite(paths: Sequence[Path]) -> bool:
    message = "Existing projects found:\n" + "\n".join(str(path) for path in paths)
    response = QMessageBox.question(
        None,
        "Confirm Overwrite",
        message,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    return response == QMessageBox.Yes


class ExportDialog(QDialog):
    def __init__(
        self,
        *,
        songs: Sequence[Song],
        output_dir: Path | str,
        template_path: Path | str,
        run_export_job: Callable[[ExportJobRequest], ExportJobResult] = run_export_job,
        confirm_overwrite: Callable[[Sequence[Path]], bool] = _default_confirm_overwrite,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("exportDialog")
        self.setWindowTitle("Generate Projects")

        self._songs = list(songs)
        self._output_dir = Path(output_dir)
        self._template_path = Path(template_path)
        self._run_export_job = run_export_job
        self._confirm_overwrite = confirm_overwrite

        self.summary_label = QLabel(self._summary_text(), self)
        self.summary_label.setObjectName("exportSummary")
        self.status_label = QLabel("Ready", self)
        self.status_label.setObjectName("exportStatus")

        self.export_button = QPushButton("Generate", self)
        self.export_button.clicked.connect(self.run_export)

        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.reject)

        button_box = QDialogButtonBox(self)
        button_box.addButton(self.export_button, QDialogButtonBox.AcceptRole)
        button_box.addButton(close_button, QDialogButtonBox.RejectRole)

        layout = QVBoxLayout(self)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.status_label)
        layout.addWidget(button_box)

    def _summary_text(self) -> str:
        count = len(self._songs)
        noun = "song" if count == 1 else "songs"
        return f"{count} {noun} selected for export\nDestination: {self._output_dir}"

    def _format_blocked_message(self, result: ExportJobResult) -> str:
        if result.warnings:
            return "Export blocked: " + " | ".join(result.warnings)
        if result.invalid_songs:
            return "Export blocked: " + ", ".join(result.invalid_songs)
        return "Export blocked"

    def run_export(self) -> ExportJobResult | None:
        if not self._songs:
            self.status_label.setText("No songs selected")
            return None

        request = ExportJobRequest(
            songs=self._songs,
            output_dir=self._output_dir,
            template_path=self._template_path,
            overwrite=False,
        )
        result = self._run_export_job(request)

        if result.status == "needs_confirmation":
            self.status_label.setText("Overwrite confirmation required")
            if not self._confirm_overwrite(result.overwrite_targets):
                self.status_label.setText("Export cancelled")
                return result

            request.overwrite = True
            result = self._run_export_job(request)

        if result.status == "error":
            self.status_label.setText(self._format_blocked_message(result))
            return result

        exported_count = len(result.exported_paths)
        noun = "project" if exported_count == 1 else "projects"
        self.status_label.setText(f"Exported {exported_count} {noun} to {self._output_dir}")
        return result
