from __future__ import annotations

import json
from pathlib import Path

from setandnotes.services.file_scan import scan_media_folder
from setandnotes.services.media_probe import FFProbeMediaProbe


class RecordingProbe:
    def __init__(self) -> None:
        self.seen: list[Path] = []

    def probe(self, path: Path) -> dict[str, str]:
        self.seen.append(path)
        return {"path": str(path)}


def test_scan_media_folder_ignores_unsupported_files(tmp_path: Path):
    supported = tmp_path / "Band - FOH.wav"
    unsupported = tmp_path / "notes.txt"
    another_supported = tmp_path / "Band - TC.wav"

    supported.write_text("audio", encoding="utf-8")
    unsupported.write_text("not media", encoding="utf-8")
    another_supported.write_text("audio", encoding="utf-8")

    probe = RecordingProbe()

    results = scan_media_folder(tmp_path, probe=probe)

    assert probe.seen == [supported, another_supported]
    assert [result["path"] for result in results] == [str(supported), str(another_supported)]


def test_ffprobe_media_probe_is_runner_stubbed():
    calls: list[list[str]] = []

    def runner(command: list[str], capture_output: bool, text: bool, check: bool):
        calls.append(command)

        class Completed:
            stdout = json.dumps(
                {
                    "format": {"duration": "12.5"},
                    "streams": [{"codec_type": "audio"}],
                }
            )

        return Completed()

    probe = FFProbeMediaProbe(runner=runner)
    result = probe.probe(Path("/tmp/song.wav"))

    assert calls == [[
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        "/tmp/song.wav",
    ]]
    assert result["format"]["duration"] == "12.5"
