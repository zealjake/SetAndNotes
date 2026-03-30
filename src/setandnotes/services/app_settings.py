from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AppSettings:
    global_rpp_template_path: str | None = None
    last_project_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "global_rpp_template_path": self.global_rpp_template_path,
            "last_project_path": self.last_project_path,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppSettings":
        return cls(
            global_rpp_template_path=payload.get("global_rpp_template_path"),
            last_project_path=payload.get("last_project_path"),
        )


def default_app_settings_path() -> Path:
    return Path.home() / "Library" / "Application Support" / "SetAndNotes" / "settings.json"


def load_app_settings(path: Path | str) -> AppSettings:
    source = Path(path)
    if not source.exists():
        return AppSettings()

    with source.open("r", encoding="utf-8") as handle:
        payload: dict[str, Any] = json.load(handle)
    return AppSettings.from_dict(payload)


def save_app_settings(settings: AppSettings, path: Path | str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(target.parent),
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(settings.to_dict(), handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temp_path = Path(handle.name)

    os.replace(str(temp_path), str(target))
