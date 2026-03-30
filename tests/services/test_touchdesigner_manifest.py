from __future__ import annotations

import json
from pathlib import Path

from setandnotes.models.library import Library


def test_import_touchdesigner_manifest_attaches_session_to_library(tmp_path: Path):
    from setandnotes.services.touchdesigner_manifest import import_touchdesigner_manifest

    library_path = tmp_path / "tour-set.zeal"
    library = Library(project_name="Tour Prep", library_path=str(library_path))
    manifest_path = tmp_path / "BandRehearsal_session.json"
    manifest_path.write_text(
        json.dumps(
            {
                "session_name": "BandRehearsal",
                "fps": "25",
                "recordings": [
                    {
                        "source_id": "camA",
                        "path": "/Users/jake/Movies/SetAndNotesCapture/camA.mov",
                        "tc_start": "01:00:00:00",
                        "tc_end": "01:10:00:00",
                    }
                ],
                "events": [{"type": "record_stop", "tc_value": "01:10:00:00"}],
                "markers": [{"song_name": "Marker", "tc_value": "01:05:00:00"}],
            }
        ),
        encoding="utf-8",
    )

    saved_payloads: list[dict[str, object]] = []

    def fake_save_library(updated_library: Library, path: Path | str) -> None:
        saved_payloads.append(updated_library.to_dict())

    updated = import_touchdesigner_manifest(library, manifest_path, save_library=fake_save_library)

    assert updated.touchdesigner_sessions[0]["session_name"] == "BandRehearsal"
    assert updated.touchdesigner_sessions[0]["manifest_path"] == str(manifest_path)
    assert updated.touchdesigner_sessions[0]["recordings"][0]["source_id"] == "camA"
    assert saved_payloads


def test_import_touchdesigner_manifest_replaces_existing_session_with_same_path(tmp_path: Path):
    from setandnotes.services.touchdesigner_manifest import import_touchdesigner_manifest

    manifest_path = tmp_path / "BandRehearsal_session.json"
    manifest_path.write_text(
        json.dumps(
            {
                "session_name": "BandRehearsalV2",
                "fps": "30",
                "recordings": [],
                "events": [],
                "markers": [],
            }
        ),
        encoding="utf-8",
    )

    library = Library(project_name="Tour Prep")
    library.touchdesigner_sessions.append(
        {
            "session_name": "BandRehearsal",
            "fps": "25",
            "manifest_path": str(manifest_path),
            "recordings": [{"source_id": "camA"}],
            "events": [],
            "markers": [],
        }
    )

    updated = import_touchdesigner_manifest(library, manifest_path, save_library=lambda *_args, **_kwargs: None)

    assert len(updated.touchdesigner_sessions) == 1
    assert updated.touchdesigner_sessions[0]["session_name"] == "BandRehearsalV2"
    assert updated.touchdesigner_sessions[0]["fps"] == "30"
