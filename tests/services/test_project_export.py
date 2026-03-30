from pathlib import Path

import pytest

from setandnotes.models.song import Song
from setandnotes.models.version import SongVersion


def test_template_rpp_renders_placeholder_tokens(tmp_path: Path):
    from setandnotes.services.template_rpp import TemplateRpp

    template_path = tmp_path / "template.rpp"
    template_path.write_text(
        "\n".join(
            [
                "NAME={{SONG_LONG_NAME}}",
                "OFFSET={{PROJECT_OFFSET}}",
                "BPM={{BPM}}",
                "MAIN={{MAIN_AUDIO_PATH}}",
                "TC={{TC_AUDIO_PATH}}",
            ]
        ),
        encoding="utf-8",
    )

    template = TemplateRpp.load(template_path)
    rendered = template.render(
        song_long_name="Opening Song",
        project_offset="01:00:00:00",
        bpm=128.0,
        main_audio_path="/media/v2/opening_foh.wav",
        tc_audio_path="/media/v2/opening_tc.wav",
    )

    assert rendered == "\n".join(
        [
            "NAME=Opening Song",
            "OFFSET=01:00:00:00",
            "BPM=128.0",
            "MAIN=/media/v2/opening_foh.wav",
            "TC=/media/v2/opening_tc.wav",
        ]
    )


def test_export_song_project_writes_sanitized_filename(tmp_path: Path):
    from setandnotes.services.project_export import export_song_project, read_song_project_id

    main_source = tmp_path / "source" / "opening_foh.wav"
    tc_source = tmp_path / "source" / "opening_tc.wav"
    main_source.parent.mkdir(parents=True, exist_ok=True)
    main_source.write_text("main audio", encoding="utf-8")
    tc_source.write_text("tc audio", encoding="utf-8")

    template_path = tmp_path / "template.rpp"
    template_path.write_text("{{SONG_LONG_NAME}}|{{PROJECT_OFFSET}}|{{BPM}}|{{MAIN_AUDIO_PATH}}|{{TC_AUDIO_PATH}}", encoding="utf-8")

    song = Song(song_id="song-1", long_name="My / Opening Song", bpm=128.0)
    song.attach_version(
        SongVersion(
            version_id="v2",
            song_id="song-1",
            label="v2",
            source_folder="/media/v2",
            source_type="rehearsal",
            main_audio_path=str(main_source),
            tc_audio_path=str(tc_source),
            decoded_tc_start="01:00:00:00",
            duration_seconds=183.25,
        )
    ).select_active_version("v2")

    output_path = export_song_project(song, template_path=template_path, output_dir=tmp_path)

    song_dir = tmp_path / "My _ Opening Song"
    media_dir = song_dir / "Media"

    assert output_path == song_dir / "My _ Opening Song.rpp"
    rendered = output_path.read_text(encoding="utf-8")
    assert f"My / Opening Song|3600.0|128.0|{media_dir / 'opening_foh.wav'}|{media_dir / 'opening_tc.wav'}" in rendered
    assert f"SETANDNOTES_SONG_PROJECT_ID {{{song.song_project_id}}}" in rendered
    assert (media_dir / "opening_foh.wav").read_text(encoding="utf-8") == "main audio"
    assert (media_dir / "opening_tc.wav").read_text(encoding="utf-8") == "tc audio"
    assert read_song_project_id(output_path) == song.song_project_id


def test_export_song_project_updates_existing_song_workspace_in_place(tmp_path: Path):
    from setandnotes.services.project_export import export_song_project

    main_source = tmp_path / "source" / "opening_foh.wav"
    tc_source = tmp_path / "source" / "opening_tc.wav"
    main_source.parent.mkdir(parents=True, exist_ok=True)
    main_source.write_text("main audio v1", encoding="utf-8")
    tc_source.write_text("tc audio v1", encoding="utf-8")

    template_path = tmp_path / "template.rpp"
    template_path.write_text("{{MAIN_AUDIO_PATH}}|{{TC_AUDIO_PATH}}", encoding="utf-8")

    song = Song(song_id="song-1", long_name="Opening Song", bpm=128.0)
    song.attach_version(
        SongVersion(
            version_id="v2",
            song_id="song-1",
            label="v2",
            source_folder="/media/v2",
            source_type="rehearsal",
            main_audio_path=str(main_source),
            tc_audio_path=str(tc_source),
            decoded_tc_start="01:00:00:00",
            duration_seconds=183.25,
        )
    ).select_active_version("v2")

    first_output = export_song_project(song, template_path=template_path, output_dir=tmp_path)
    main_source.write_text("main audio v2", encoding="utf-8")
    tc_source.write_text("tc audio v2", encoding="utf-8")
    second_output = export_song_project(song, template_path=template_path, output_dir=tmp_path)

    song_dir = tmp_path / "Opening Song"
    media_dir = song_dir / "Media"

    assert first_output == second_output == song_dir / "Opening Song.rpp"
    assert (media_dir / "opening_foh.wav").read_text(encoding="utf-8") == "main audio v2"
    assert (media_dir / "opening_tc.wav").read_text(encoding="utf-8") == "tc audio v2"


def test_export_song_project_blocks_missing_required_values(tmp_path: Path):
    from setandnotes.services.project_export import export_song_project

    template_path = tmp_path / "template.rpp"
    template_path.write_text("{{SONG_LONG_NAME}}", encoding="utf-8")

    song = Song(song_id="song-1", long_name="Opening Song")

    with pytest.raises(ValueError, match="missing required export values"):
        export_song_project(song, template_path=template_path, output_dir=tmp_path)


def test_render_reaper_project_patches_real_template_tracks(tmp_path: Path):
    from setandnotes.services.template_rpp import TemplateRpp

    template_path = tmp_path / "MAToolsTemplate.rpp"
    template_path.write_text(
        "\n".join(
            [
                "<REAPER_PROJECT 0.1 \"7.10/x64\" 1735774321",
                "  PROJOFFS 0 0 0",
                "  TEMPO 115.99 4 4 0",
                "  <TRACK {11111111-1111-1111-1111-111111111111}",
                '    NAME "TC"',
                "  >",
                "  <TRACK {22222222-2222-2222-2222-222222222222}",
                '    NAME "TRACK"',
                "  >",
                "  <TRACK {33333333-3333-3333-3333-333333333333}",
                '    NAME "TC Record"',
                "  >",
                "  <TRACK {44444444-4444-4444-4444-444444444444}",
                '    NAME "TRACK Record"',
                "  >",
                "  <TRACK {55555555-5555-5555-5555-555555555555}",
                '    NAME "Video_Multicam"',
                "  >",
                "  <TRACK {66666666-6666-6666-6666-666666666666}",
                '    NAME "Video_Wide"',
                "  >",
                ">",
            ]
        ),
        encoding="utf-8",
    )

    template = TemplateRpp.load(template_path)
    rendered = template.render_reaper_project(
        project_offset_seconds=3723.5,
        bpm=128.25,
        track_media_path="/sessions/set/SONGNAME/Media/SongTrack.wav",
        tc_media_path="/sessions/set/SONGNAME/Media/SongTC.wav",
        track_length_seconds=183.25,
        tc_length_seconds=183.25,
        track_name="OpeningSong_Track",
        tc_name="OpeningSong_TC",
        multicam_video_path="/sessions/set/SONGNAME/Media/OpeningSong_Multicam.mov",
        wide_video_path="/sessions/set/SONGNAME/Media/OpeningSong_WideShot1080.mov",
        multicam_length_seconds=183.25,
        wide_length_seconds=183.25,
        multicam_name="OpeningSong_Multicam",
        wide_name="OpeningSong_Wide",
    )

    assert "PROJOFFS 3723.5 0 0" in rendered
    assert "TEMPO 128.25 4 4 0" in rendered
    assert 'NAME "TC Record"' in rendered
    assert 'NAME "TRACK Record"' in rendered
    assert 'NAME "OpeningSong_Track"' in rendered
    assert 'NAME "OpeningSong_TC"' in rendered
    assert 'NAME "OpeningSong_Multicam"' in rendered
    assert 'NAME "OpeningSong_Wide"' in rendered
    assert "FILE \"Media/SongTrack.wav\"" in rendered
    assert "FILE \"Media/SongTC.wav\"" in rendered
    assert "FILE \"Media/OpeningSong_Multicam.mov\"" in rendered
    assert "FILE \"Media/OpeningSong_WideShot1080.mov\"" in rendered
    assert rendered.count("<ITEM") == 4


def test_render_reaper_project_inserts_tempo_point_at_tc_entry_offset(tmp_path: Path):
    from setandnotes.services.template_rpp import TemplateRpp

    template_path = tmp_path / "MAToolsTemplate.rpp"
    template_path.write_text(
        "\n".join(
            [
                "<REAPER_PROJECT 0.1 \"7.10/x64\" 1735774321",
                "  PROJOFFS 0 0 0",
                "  TEMPO 115.99 4 4 0",
                "  <TEMPOENVEX",
                "    EGUID {6EF717F6-0A89-EF49-A6CC-DBA2CA016C1F}",
                "    ACT 0 -1",
                "    VIS 1 0 1",
                "    LANEHEIGHT 0 0",
                "    ARM 0",
                "    DEFSHAPE 1 -1 -1",
                "  >",
                "  <TRACK {11111111-1111-1111-1111-111111111111}",
                '    NAME "TC"',
                "  >",
                "  <TRACK {22222222-2222-2222-2222-222222222222}",
                '    NAME "TRACK"',
                "  >",
                ">",
            ]
        ),
        encoding="utf-8",
    )

    template = TemplateRpp.load(template_path)
    rendered = template.render_reaper_project(
        project_offset_seconds=3700.5,
        bpm=128.25,
        track_media_path="/sessions/set/SONGNAME/Media/SongTrack.wav",
        tc_media_path="/sessions/set/SONGNAME/Media/SongTC.wav",
        track_length_seconds=183.25,
        tc_length_seconds=183.25,
        track_name="OpeningSong_Track",
        tc_name="OpeningSong_TC",
        tc_entry_offset_seconds=23.0,
    )

    assert "PROJOFFS 3700.5 0 0" in rendered
    assert "TEMPO 115.99 4 4 0" in rendered
    assert "PT 0.000000000000 115.9900000000 1 262148" in rendered
    assert "PT 23.000000000000 128.2500000000 1 262148" in rendered


def test_export_song_project_uses_real_template_structure(tmp_path: Path):
    from setandnotes.services.project_export import export_song_project

    source_root = tmp_path / "source"
    source_root.mkdir(parents=True, exist_ok=True)
    main_source = source_root / "opening_foh.wav"
    tc_source = source_root / "opening_tc.wav"
    multicam_source = source_root / "Opening Song_Multicam_TC01_00_00_00.mov"
    wide_source = source_root / "Opening Song_WideShot1080_TC01_00_00_00.mov"
    main_source.write_text("main audio", encoding="utf-8")
    tc_source.write_text("tc audio", encoding="utf-8")
    multicam_source.write_text("multicam video", encoding="utf-8")
    wide_source.write_text("wide video", encoding="utf-8")

    template_path = tmp_path / "MAToolsTemplate.rpp"
    template_path.write_text(
        "\n".join(
            [
                "<REAPER_PROJECT 0.1 \"7.10/x64\" 1735774321",
                "  PROJOFFS 0 0 0",
                "  TEMPO 115.99 4 4 0",
                "  <TRACK {11111111-1111-1111-1111-111111111111}",
                '    NAME "TC"',
                "  >",
                "  <TRACK {22222222-2222-2222-2222-222222222222}",
                '    NAME "TRACK"',
                "  >",
                "  <TRACK {33333333-3333-3333-3333-333333333333}",
                '    NAME "TC Record"',
                "  >",
                "  <TRACK {44444444-4444-4444-4444-444444444444}",
                '    NAME "TRACK Record"',
                "  >",
                "  <TRACK {55555555-5555-5555-5555-555555555555}",
                '    NAME "Video_Multicam"',
                "  >",
                "  <TRACK {66666666-6666-6666-6666-666666666666}",
                '    NAME "Video_Wide"',
                "  >",
                ">",
            ]
        ),
        encoding="utf-8",
    )

    song = Song(song_id="song-1", long_name="Opening Song", bpm=128.25)
    song.attach_version(
        SongVersion(
            version_id="v2",
            song_id="song-1",
            label="v2",
            source_folder=str(source_root),
            source_type="rehearsal",
            main_audio_path=str(main_source),
            tc_audio_path=str(tc_source),
            decoded_tc_start="3723.5",
            duration_seconds=183.25,
            video_assets={
                "Multicam": str(multicam_source),
                "WideShot1080": str(wide_source),
            },
        )
    ).select_active_version("v2")

    output_path = export_song_project(song, template_path=template_path, output_dir=tmp_path)
    rendered = output_path.read_text(encoding="utf-8")

    assert "PROJOFFS 3723.5 0 0" in rendered
    assert "TEMPO 128.25 4 4 0" in rendered
    assert rendered.count("<ITEM") == 4
    assert 'NAME "TC Record"' in rendered
    assert 'NAME "TRACK Record"' in rendered
    assert 'NAME "Opening Song_Track"' in rendered
    assert 'NAME "Opening Song_TC"' in rendered
    assert 'NAME "Opening Song_Multicam"' in rendered
    assert 'NAME "Opening Song_Wide"' in rendered
    assert "FILE \"Media/Opening Song_Multicam_TC01_00_00_00.mov\"" in rendered
    assert "FILE \"Media/Opening Song_WideShot1080_TC01_00_00_00.mov\"" in rendered
    media_dir = output_path.parent / "Media"
    assert (media_dir / multicam_source.name).read_text(encoding="utf-8") == "multicam video"
    assert (media_dir / wide_source.name).read_text(encoding="utf-8") == "wide video"


def test_export_song_project_uses_tc_entry_offset_for_project_offset_and_tempo_map(tmp_path: Path):
    from setandnotes.services.project_export import export_song_project

    source_root = tmp_path / "source"
    source_root.mkdir(parents=True, exist_ok=True)
    main_source = source_root / "opening_foh.wav"
    tc_source = source_root / "opening_tc.wav"
    main_source.write_text("main audio", encoding="utf-8")
    tc_source.write_text("tc audio", encoding="utf-8")

    template_path = tmp_path / "MAToolsTemplate.rpp"
    template_path.write_text(
        "\n".join(
            [
                "<REAPER_PROJECT 0.1 \"7.10/x64\" 1735774321",
                "  PROJOFFS 0 0 0",
                "  TEMPO 115.99 4 4 0",
                "  <TEMPOENVEX",
                "    EGUID {6EF717F6-0A89-EF49-A6CC-DBA2CA016C1F}",
                "    ACT 0 -1",
                "    VIS 1 0 1",
                "    LANEHEIGHT 0 0",
                "    ARM 0",
                "    DEFSHAPE 1 -1 -1",
                "  >",
                "  <TRACK {11111111-1111-1111-1111-111111111111}",
                '    NAME "TC"',
                "  >",
                "  <TRACK {22222222-2222-2222-2222-222222222222}",
                '    NAME "TRACK"',
                "  >",
                ">",
            ]
        ),
        encoding="utf-8",
    )

    song = Song(song_id="song-1", long_name="Opening Song", bpm=128.25)
    song.attach_version(
        SongVersion(
            version_id="v2",
            song_id="song-1",
            label="v2",
            source_folder=str(source_root),
            source_type="rehearsal",
            main_audio_path=str(main_source),
            tc_audio_path=str(tc_source),
            decoded_tc_start="01:00:00:00",
            tc_entry_offset_seconds=23.0,
            duration_seconds=183.25,
        )
    ).select_active_version("v2")

    output_path = export_song_project(song, template_path=template_path, output_dir=tmp_path)
    rendered = output_path.read_text(encoding="utf-8")

    assert "PROJOFFS 3577.0 0 0" in rendered
    assert "TEMPO 115.99 4 4 0" in rendered
    assert "PT 0.000000000000 115.9900000000 1 262148" in rendered
    assert "PT 23.000000000000 128.2500000000 1 262148" in rendered


def test_render_real_matools_template_from_disk(tmp_path: Path):
    from setandnotes.services.template_rpp import TemplateRpp

    template_path = Path("/Users/jake/Library/Application Support/REAPER/ProjectTemplates/MAToolsTemplate.rpp")
    if not template_path.exists():
        pytest.skip("real MATools template not available")

    template = TemplateRpp.load(template_path)
    rendered = template.render_reaper_project(
        project_offset_seconds=3723.5,
        bpm=128.25,
        track_media_path="/sessions/set/SONGNAME/Media/SongTrack.wav",
        tc_media_path="/sessions/set/SONGNAME/Media/SongTC.wav",
        track_length_seconds=183.25,
        tc_length_seconds=183.25,
        track_name="OpeningSong_Track",
        tc_name="OpeningSong_TC",
    )

    assert "PROJOFFS 3723.5 0 0" in rendered
    assert "TEMPO 128.25 4 4 0" in rendered
    assert rendered.count("<ITEM") == 2
    assert 'NAME "TC Record"' in rendered
    assert 'NAME "TRACK Record"' in rendered
    assert 'NAME "OpeningSong_Track"' in rendered
    assert 'NAME "OpeningSong_TC"' in rendered
