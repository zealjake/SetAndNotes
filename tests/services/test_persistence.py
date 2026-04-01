from pathlib import Path

import pytest

from setandnotes.models.library import Library
from setandnotes.models.song import Song
from setandnotes.models.version import SongVersion


def build_library() -> Library:
    song = Song(song_id="song-1", long_name="Opening Song", bpm=128.0)
    version = SongVersion(
        version_id="v1",
        song_id="song-1",
        label="prep",
        source_folder="/media/v1",
        source_type="prep",
        main_audio_path="/media/v1/opening_song_foh.wav",
        tc_audio_path="/media/v1/opening_song_tc.wav",
        decoded_tc_start="01:00:00:00",
        tc_entry_offset_seconds=23.0,
    )
    return Library(project_name="Tour Prep").add_song(song.attach_version(version))


def test_save_and_load_library_round_trip(tmp_path: Path):
    from setandnotes.services.persistence import load_library, save_library

    library = build_library()
    target = tmp_path / "library.json"

    save_library(library, target)

    restored = load_library(target)

    assert restored.project_name == "Tour Prep"
    assert restored.library_path == str(target)
    assert restored.song_by_id("song-1").active_version().decoded_tc_start == "01:00:00:00"
    assert restored.song_by_id("song-1").active_version().tc_entry_offset_seconds == 23.0
    assert target.exists()


def test_save_and_load_library_round_trip_preserves_web_note_users(tmp_path: Path):
    from setandnotes.services.persistence import load_library, save_library

    library = build_library()
    library.web_note_users = [
        {"username": "CreativeDirector", "token": "tok-creative", "enabled": True},
        {"username": "VideoDirector", "token": "tok-video", "enabled": False},
    ]
    target = tmp_path / "library.json"

    save_library(library, target)

    restored = load_library(target)

    assert restored.web_note_users == [
        {"username": "CreativeDirector", "token": "tok-creative", "enabled": True},
        {"username": "VideoDirector", "token": "tok-video", "enabled": False},
    ]


def test_save_library_uses_atomic_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from setandnotes.services import persistence

    library = build_library()
    target = tmp_path / "library.json"
    calls: list[tuple[str, str]] = []

    def fake_replace(source: str, destination: str) -> None:
        calls.append((source, destination))
        Path(destination).write_text(Path(source).read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setattr(persistence.os, "replace", fake_replace)

    persistence.save_library(library, target)

    assert calls
    assert calls[0][1] == str(target)
