from setandnotes.services.web_note_users import (
    build_copy_all_web_note_links_text,
    build_web_note_url,
    create_web_note_user,
    ensure_web_note_user_token,
    set_web_note_user_enabled,
    slugify_web_note_username,
)


def test_create_web_note_user_builds_enabled_user_with_token() -> None:
    user = create_web_note_user("CreativeDirector")

    assert user["username"] == "CreativeDirector"
    assert isinstance(user["token"], str)
    assert user["token"]
    assert user["slug"] == "creativedirector"
    assert user["enabled"] is True


def test_ensure_web_note_user_token_preserves_existing_token() -> None:
    user = {"username": "Lighting", "token": "existing-token", "enabled": True}

    normalized = ensure_web_note_user_token(user)

    assert normalized["token"] == "existing-token"


def test_set_web_note_user_enabled_updates_enabled_flag() -> None:
    user = {"username": "Content", "token": "tok-content", "enabled": True}

    updated = set_web_note_user_enabled(user, False)

    assert updated["enabled"] is False


def test_build_web_note_url_uses_host_port_and_token() -> None:
    assert (
        build_web_note_url("192.168.1.50", 8787, "video-director")
        == "http://192.168.1.50:8787/notes/u/video-director"
    )


def test_slugify_web_note_username_normalizes_name() -> None:
    assert slugify_web_note_username("Video Director") == "video-director"
    assert slugify_web_note_username("Lighting/Lasers") == "lighting-lasers"


def test_build_copy_all_web_note_links_text_formats_message() -> None:
    text = build_copy_all_web_note_links_text(
        [
            {"username": "USER 1", "slug": "user-1"},
            {"username": "USER 2", "slug": "user-2"},
        ],
        host="192.168.1.50",
        port=8787,
    )

    assert text == (
        "USER 1\nhttp://192.168.1.50:8787/notes/u/user-1\n\n"
        "USER 2\nhttp://192.168.1.50:8787/notes/u/user-2"
    )
