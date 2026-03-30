from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class Runner(Protocol):
    def __call__(
        self,
        command: list[str],
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> Any: ...


@dataclass(frozen=True, slots=True)
class LtcDecodeResult:
    status: str
    first_timecode: str | None
    fps: str | None
    drop_frame: bool | None
    confidence: float
    raw_output: str = ""


def _default_runner(command: list[str], capture_output: bool, text: bool, check: bool):
    return subprocess.run(command, capture_output=capture_output, text=text, check=check)


_TIMECODE_RE = re.compile(
    r"^\s*[0-9A-Fa-f]+\s+(?P<timecode>\d{2}:\d{2}:\d{2}(?P<separator>[:.])(?P<frame>\d{2}))\s+\|"
)


def _infer_fps(frames: list[tuple[str, int]]) -> str | None:
    if not frames:
        return None

    first_timecode, _ = frames[0]
    separator = ":" if ":" in first_timecode else "."
    max_frame = max(frame for _, frame in frames)

    if separator == ".":
        return "30000/1001" if max_frame >= 29 else None

    if max_frame == 23:
        return "24/1"
    if max_frame == 24:
        return "25/1"
    if max_frame == 29:
        return "30/1"
    return None


def _parse_ltcdump_output(output: str) -> LtcDecodeResult:
    first_timecode: str | None = None
    first_second: str | None = None
    frames_in_first_second: list[tuple[str, int]] = []
    drop_frame: bool | None = None

    for line in output.splitlines():
        match = _TIMECODE_RE.match(line)
        if not match:
            continue

        timecode = match.group("timecode")
        separator = match.group("separator")
        frame = int(match.group("frame"))

        if drop_frame is None:
            drop_frame = separator == "."

        if first_timecode is None:
            first_timecode = timecode
            first_second = timecode[:8]
            frames_in_first_second.append((timecode, frame))
            continue

        if timecode[:8] == first_second:
            frames_in_first_second.append((timecode, frame))
        elif frames_in_first_second:
            break

    fps = _infer_fps(frames_in_first_second)

    if first_timecode is None:
        return LtcDecodeResult(
            status="failed",
            first_timecode=None,
            fps=fps,
            drop_frame=drop_frame,
            confidence=0.0,
            raw_output=output,
        )

    return LtcDecodeResult(
        status="ok",
        first_timecode=first_timecode,
        fps=fps,
        drop_frame=drop_frame,
        confidence=1.0,
        raw_output=output,
    )


def decode_ltc_audio(
    path: Path | str,
    *,
    ltcdump_bin: str = "/opt/homebrew/bin/ltcdump",
    runner: Runner = _default_runner,
) -> LtcDecodeResult:
    source = Path(path)
    command = [ltcdump_bin, "-F", str(source)]

    try:
        completed = runner(command, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as error:
        output = ""
        if getattr(error, "stdout", None):
            output += error.stdout
        if getattr(error, "stderr", None):
            output += error.stderr
        return LtcDecodeResult(
            status="failed",
            first_timecode=None,
            fps=None,
            drop_frame=None,
            confidence=0.0,
            raw_output=output,
        )

    output = completed.stdout or ""
    return _parse_ltcdump_output(output)
