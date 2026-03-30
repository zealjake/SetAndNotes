from __future__ import annotations

import json
from pathlib import Path

from setandnotes.touchdesigner.capture_controller import CaptureController


def test_capture_controller_tracks_record_ranges_and_markers(tmp_path: Path):
    controller = CaptureController(
        session_name="BandRehearsal",
        output_root=tmp_path,
        fps="25",
    )

    source_paths = {
        "camA": controller.build_record_path("camA", timestamp_token="20260321_100000"),
        "camB": controller.build_record_path("camB", timestamp_token="20260321_100000"),
    }

    controller.start_recording(tc_start="01:00:00:00", source_paths=source_paths)
    controller.add_marker("OpeningSong", tc_value="01:02:10:00")
    controller.add_marker("SecondSong", tc_value="01:08:00:00")
    controller.stop_recording(tc_end="01:15:45:12")

    manifest = controller.build_manifest()

    assert manifest["session_name"] == "BandRehearsal"
    assert manifest["fps"] == "25"
    assert manifest["recordings"][0]["source_id"] == "camA"
    assert manifest["recordings"][0]["tc_start"] == "01:00:00:00"
    assert manifest["recordings"][0]["tc_end"] == "01:15:45:12"
    assert manifest["markers"][0]["song_name"] == "OpeningSong"
    assert manifest["markers"][1]["tc_value"] == "01:08:00:00"


def test_capture_controller_writes_manifest_json(tmp_path: Path):
    controller = CaptureController(
        session_name="BandRehearsal",
        output_root=tmp_path,
        fps="30",
    )
    source_paths = {"camA": controller.build_record_path("camA", timestamp_token="20260321_100000")}

    controller.start_recording(tc_start="02:00:00:00", source_paths=source_paths)
    controller.stop_recording(tc_end="02:10:00:00")

    manifest_path = controller.write_manifest()

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_path == tmp_path / "BandRehearsal_session.json"
    assert payload["fps"] == "30"
    assert payload["recordings"][0]["path"].endswith("camA_20260321_100000.mov")


def test_capture_controller_rejects_stop_before_start(tmp_path: Path):
    controller = CaptureController(
        session_name="BandRehearsal",
        output_root=tmp_path,
        fps="25",
    )

    try:
        controller.stop_recording(tc_end="01:10:00:00")
    except RuntimeError as exc:
        assert "not recording" in str(exc).lower()
    else:  # pragma: no cover - defensive failure
        raise AssertionError("Expected stop_recording to reject idle state")
