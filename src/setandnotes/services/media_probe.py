from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


class MediaProbe(Protocol):
    def probe(self, path: Path) -> dict[str, Any]:
        """Probe a media file and return structured metadata."""


def _default_runner(command: list[str], capture_output: bool, text: bool, check: bool):
    return subprocess.run(command, capture_output=capture_output, text=text, check=check)


@dataclass(slots=True)
class FFProbeMediaProbe:
    ffprobe_bin: str = "ffprobe"
    runner: Any = field(default=_default_runner)

    def probe(self, path: Path) -> dict[str, Any]:
        command = [
            self.ffprobe_bin,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        completed = self.runner(command, capture_output=True, text=True, check=True)
        return json.loads(completed.stdout)
