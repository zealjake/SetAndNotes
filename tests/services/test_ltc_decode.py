from __future__ import annotations

import wave
from pathlib import Path


LTCGEN_BIN = "/opt/homebrew/bin/ltcgen"


def test_decode_ltc_audio_returns_first_timecode_and_format(tmp_path: Path):
    from setandnotes.services.ltc_decode import decode_ltc_audio

    fixture = tmp_path / "sample.wav"

    import subprocess

    subprocess.run(
        [
            LTCGEN_BIN,
            "-f",
            "25/1",
            "-t",
            "01:23:45:00",
            "-l",
            "00:00:02:00",
            str(fixture),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = decode_ltc_audio(fixture)

    assert result.status == "ok"
    assert result.first_timecode == "01:23:45:00"
    assert result.fps == "25/1"
    assert result.drop_frame is False
    assert result.confidence == 1.0


def test_decode_ltc_audio_reports_failed_decode(tmp_path: Path):
    from setandnotes.services.ltc_decode import decode_ltc_audio

    silent = tmp_path / "silent.wav"
    with wave.open(str(silent), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(48000)
        handle.writeframes(b"\x00\x00" * 480)

    result = decode_ltc_audio(silent)

    assert result.status == "failed"
    assert result.first_timecode is None
    assert result.fps is None
    assert result.drop_frame is None
    assert result.confidence == 0.0
