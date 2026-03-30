from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from setandnotes.models.library import Library


def save_library(library: Library, path: Path | str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = library.to_dict()
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(target.parent),
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temp_path = Path(handle.name)

    os.replace(str(temp_path), str(target))
    library.library_path = str(target)


def load_library(path: Path | str) -> Library:
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        payload: dict[str, Any] = json.load(handle)

    library = Library.from_dict(payload)
    library.library_path = str(source)
    return library
