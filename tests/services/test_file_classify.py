from setandnotes.services.file_classify import classify_media_file, normalize_media_name


def test_normalize_media_name_strips_role_tokens_and_collapses_separators():
    assert normalize_media_name("  My___Song--FOH Master  ") == "my_song"


def test_classify_media_file_identifies_main_audio_candidates():
    result = classify_media_file("/media/v1/My Song - L-R.wav")

    assert result.role == "main"
    assert result.normalized_name == "my_song"


def test_classify_media_file_identifies_timecode_candidates():
    result = classify_media_file("My Song SMPTE.wav")

    assert result.role == "tc"
    assert result.normalized_name == "my_song"


def test_classify_media_file_marks_conflicting_tokens_as_ambiguous():
    result = classify_media_file("My Song track timecode.wav")

    assert result.role == "ambiguous"
    assert result.normalized_name == "my_song"
