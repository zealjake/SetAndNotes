from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from setandnotes.models.library import Library
from setandnotes.services.persistence import save_library

SaveLibrary = Callable[[Library, Path | str], None]


def import_touchdesigner_manifest(
    library: Library,
    manifest_path: Path | str,
    *,
    save_library: SaveLibrary = save_library,
) -> Library:
    path = Path(manifest_path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    session = {
        "session_name": payload.get("session_name", path.stem),
        "fps": str(payload.get("fps", "")),
        "manifest_path": str(path),
        "recordings": list(payload.get("recordings", [])),
        "events": list(payload.get("events", [])),
        "markers": list(payload.get("markers", [])),
    }

    existing_index = next(
        (index for index, existing in enumerate(library.touchdesigner_sessions) if existing.get("manifest_path") == str(path)),
        None,
    )
    if existing_index is None:
        library.touchdesigner_sessions.append(session)
    else:
        library.touchdesigner_sessions[existing_index] = session

    if library.library_path:
        save_library(library, library.library_path)

    return library
