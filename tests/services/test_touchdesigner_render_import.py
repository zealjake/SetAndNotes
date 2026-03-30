from __future__ import annotations

from pathlib import Path

from setandnotes.models.library import Library
from setandnotes.models.song import Song
from setandnotes.models.version import SongVersion


def test_parse_rendered_video_filename_extracts_song_asset_type_and_tc():
    from setandnotes.services.touchdesigner_render_import import parse_rendered_video_filename

    parsed = parse_rendered_video_filename("OpeningSong_Multicam_TC01_00_00_00.mov")

    assert parsed.long_name == "OpeningSong"
    assert parsed.asset_type == "Multicam"
    assert parsed.tc_start == "01:00:00:00"


def test_import_rendered_video_folder_attaches_video_assets_to_matching_version(tmp_path: Path):
    from setandnotes.services.touchdesigner_render_import import import_rendered_video_folder

    render_folder = tmp_path / "TDRender" / "v2"
    render_folder.mkdir(parents=True)
    multicam = render_folder / "OpeningSong_Multicam_TC01_00_00_00.mov"
    wideshot1080 = render_folder / "OpeningSong_WideShot1080_TC01_00_00_00.mov"
    multicam.write_bytes(b"multicam")
    wideshot1080.write_bytes(b"wideshot")

    song = Song(song_id="song-1", long_name="OpeningSong", bpm=128.0)
    song.attach_version(
        SongVersion(
            version_id="v2",
            song_id="song-1",
            label="v2",
            source_folder=str(render_folder),
            source_type="rehearsal",
            main_audio_path="/audio/opening_foh.wav",
            tc_audio_path="/audio/opening_tc.wav",
            decoded_tc_start="01:00:00:00",
        )
    ).select_active_version("v2")

    library = Library(project_name="Tour Prep", songs=[song])

    updated = import_rendered_video_folder(library, render_folder)
    video_assets = updated.song_by_id("song-1").active_version().video_assets

    assert set(video_assets) == {"Multicam", "WideShot1080"}
    assert video_assets["Multicam"] == str(multicam)
    assert video_assets["WideShot1080"] == str(wideshot1080)


def test_import_rendered_video_folder_warns_for_unmatched_songs(tmp_path: Path):
    from setandnotes.services.touchdesigner_render_import import import_rendered_video_folder

    render_folder = tmp_path / "TDRender" / "v2"
    render_folder.mkdir(parents=True)
    unmatched = render_folder / "UnknownSong_Multicam_TC01_00_00_00.mov"
    unmatched.write_bytes(b"wide")

    library = Library(project_name="Tour Prep")

    updated, warnings = import_rendered_video_folder(library, render_folder, return_warnings=True)

    assert updated.songs == []
    assert warnings == ["No matching song for rendered video: UnknownSong_Multicam_TC01_00_00_00.mov"]
