from __future__ import annotations

from PySide6.QtWidgets import QStatusBar


class StatusPanel(QStatusBar):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusPanel")
        self._message = "Ready"
        self._project_path: str | None = None
        self._render()

    def set_message(self, message: str) -> None:
        self._message = message
        self._render()

    def set_project_path(self, project_path: str | None) -> None:
        self._project_path = None if project_path is None else str(project_path)
        self._render()

    def set_library_path(self, library_path: str | None) -> None:
        self.set_project_path(library_path)

    def _render(self) -> None:
        parts = [self._message]
        if self._project_path:
            parts.append(self._project_path)
        self.showMessage(" | ".join(parts))
