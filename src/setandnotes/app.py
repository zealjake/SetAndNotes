from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from setandnotes.main_window import SetAndNotesMainWindow


def main() -> int:
    """Application entry point."""
    app = QApplication.instance() or QApplication(sys.argv)
    window = SetAndNotesMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
