from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


def preferred_font_families() -> list[str]:
    return ["Aktiv Grotesk", "Aktiv Grotesk Ex"]


def _pick_available_family(preferred: str) -> str | None:
    families = set(QFontDatabase.families())
    if preferred in families:
        return preferred
    return None


def activate_application_fonts(app: QApplication | None) -> dict[str, str]:
    if app is None:
        return {"body": "system", "header": "system", "subheader": "system"}

    body_family = _pick_available_family("Aktiv Grotesk") or app.font().family()
    header_family = _pick_available_family("Aktiv Grotesk Ex") or body_family
    subheader_family = header_family

    app.setFont(QFont(body_family))
    return {"body": body_family, "header": header_family, "subheader": subheader_family}

