from setandnotes.models.library import Library
from setandnotes.models.song import Song
from setandnotes.services.file_classify import ClassifiedMediaFile


def _classified(role: str, normalized_name: str, source_name: str) -> ClassifiedMediaFile:
    return ClassifiedMediaFile(role=role, normalized_name=normalized_name, source_name=source_name)


def test_match_imported_files_attaches_new_version_to_existing_song():
    from setandnotes.models.version import SongVersion
    from setandnotes.services.song_match import match_imported_files

    library = Library(project_name="Tour Prep").add_song(
        Song(song_id="opening_song", long_name="Opening Song").attach_version(
            SongVersion(
                version_id="v1",
                song_id="opening_song",
                label="prep",
                source_folder="/media/v1",
                source_type="prep",
                main_audio_path="/media/v1/opening_song_foh.wav",
                tc_audio_path="/media/v1/opening_song_tc.wav",
            )
        )
    )

    updated = match_imported_files(
        library,
        [
            _classified("main", "opening_song", "/imports/v2/Opening Song FOH.wav"),
            _classified("tc", "opening_song", "/imports/v2/Opening Song TC.wav"),
        ],
        source_folder="/imports/v2",
        version_label="v2",
        source_type="rehearsal",
    )

    song = updated.song_by_id("opening_song")
    assert song.long_name == "Opening Song"
    assert [version.version_id for version in song.versions] == ["v1", "v2"]
    assert song.active_version_id == "v1"
    assert song.versions[-1].main_audio_path == "/imports/v2/Opening Song FOH.wav"
    assert song.versions[-1].tc_audio_path == "/imports/v2/Opening Song TC.wav"


def test_match_imported_files_creates_new_song_with_stable_id():
    from setandnotes.services.song_match import match_imported_files

    library = Library(project_name="Tour Prep")

    updated = match_imported_files(
        library,
        [
            _classified("main", "new_song", "/imports/v2/New Song Master.wav"),
            _classified("tc", "new_song", "/imports/v2/New Song SMPTE.wav"),
        ],
        source_folder="/imports/v2",
        version_label="v2",
        source_type="rehearsal",
    )

    song = updated.song_by_id("new_song")
    assert song.long_name == "NewSong"
    assert song.normalized_name == "new_song"
    assert len(song.versions) == 1
    assert song.versions[0].version_id == "v2"
    assert song.versions[0].main_audio_path == "/imports/v2/New Song Master.wav"


def test_match_imported_files_normalizes_long_name_without_spaces():
    from setandnotes.services.song_match import match_imported_files

    library = Library(project_name="Tour Prep")

    updated = match_imported_files(
        library,
        [
            _classified("main", "wet_like_bouncer_edit", "/imports/v2/Wet Like Bouncer Edit FOH.wav"),
            _classified("tc", "wet_like_bouncer_edit", "/imports/v2/Wet Like Bouncer Edit TC.wav"),
        ],
        source_folder="/imports/v2",
        version_label="v2",
        source_type="rehearsal",
    )

    song = updated.song_by_id("wet_like_bouncer_edit")

    assert song.long_name == "WetLikeBouncerEdit"
    assert song.short_name == "WETL"


def test_match_imported_files_marks_ambiguous_pairs_with_warning():
    from setandnotes.services.song_match import match_imported_files

    library = Library(project_name="Tour Prep")

    updated = match_imported_files(
        library,
        [
            _classified("ambiguous", "song_x", "/imports/v3/Song X track timecode.wav"),
            _classified("main", "song_x", "/imports/v3/Song X FOH.wav"),
            _classified("tc", "song_x", "/imports/v3/Song X TC.wav"),
        ],
        source_folder="/imports/v3",
        version_label="v3",
        source_type="rehearsal",
    )

    song = updated.song_by_id("song_x")
    version = song.versions[0]

    assert version.status == "warning"
    assert any("ambiguous" in warning for warning in version.warnings)
