from __future__ import annotations

from setandnotes.services.web_note_capture import WebNoteCaptureError, WebNoteCaptureService


def test_create_capture_uses_token_user_and_captures_playhead() -> None:
    service = WebNoteCaptureService(
        project_users=[
            {"username": "CreativeDirector", "token": "tok-creative", "enabled": True},
        ],
        capture_timestamp_fn=lambda: 123.456,
        create_note_marker_fn=lambda username, note_type, body, pos_sec: {"ok": True},
    )

    capture = service.create_capture("tok-creative", "Content")

    assert capture["username"] == "CreativeDirector"
    assert capture["note_type"] == "Content"
    assert capture["playhead_sec"] == 123.456
    assert capture["capture_id"]


def test_submit_capture_creates_note_at_stored_timestamp() -> None:
    calls: list[tuple[str, str, str, float]] = []
    service = WebNoteCaptureService(
        project_users=[
            {"username": "VideoDirector", "token": "tok-video", "enabled": True},
        ],
        capture_timestamp_fn=lambda: 45.0,
        create_note_marker_fn=lambda username, note_type, body, pos_sec: calls.append((username, note_type, body, pos_sec)) or {"ok": True},
    )

    capture = service.create_capture("tok-video", "Cameras")
    result = service.submit_capture("tok-video", capture["capture_id"], "Too wide")

    assert calls == [("VideoDirector", "Cameras", "Too wide", 45.0)]
    assert result["username"] == "VideoDirector"


def test_create_capture_rejects_unknown_or_disabled_tokens() -> None:
    service = WebNoteCaptureService(
        project_users=[
            {"username": "Lighting", "token": "tok-lighting", "enabled": False},
        ],
        capture_timestamp_fn=lambda: 1.0,
        create_note_marker_fn=lambda username, note_type, body, pos_sec: {"ok": True},
    )

    try:
        service.create_capture("missing", "General")
    except WebNoteCaptureError as exc:
        assert str(exc) == "Unknown web note user"
    else:
        raise AssertionError("Expected unknown-token error")

    try:
        service.create_capture("tok-lighting", "General")
    except WebNoteCaptureError as exc:
        assert str(exc) == "Web note user is disabled"
    else:
        raise AssertionError("Expected disabled-token error")


def test_submit_capture_rejects_missing_capture_id() -> None:
    service = WebNoteCaptureService(
        project_users=[
            {"username": "Content", "token": "tok-content", "enabled": True},
        ],
        capture_timestamp_fn=lambda: 1.0,
        create_note_marker_fn=lambda username, note_type, body, pos_sec: {"ok": True},
    )

    try:
        service.submit_capture("tok-content", "missing", "Hello")
    except WebNoteCaptureError as exc:
        assert str(exc) == "Unknown or expired capture"
    else:
        raise AssertionError("Expected missing-capture error")


def test_submit_capture_rejects_blank_note_body() -> None:
    service = WebNoteCaptureService(
        project_users=[
            {"username": "Content", "token": "tok-content", "enabled": True},
        ],
        capture_timestamp_fn=lambda: 1.0,
        create_note_marker_fn=lambda username, note_type, body, pos_sec: {"ok": True},
    )

    capture = service.create_capture("tok-content", "Content")

    try:
        service.submit_capture("tok-content", capture["capture_id"], "   ")
    except WebNoteCaptureError as exc:
        assert str(exc) == "Note body is required"
    else:
        raise AssertionError("Expected blank-body error")


def test_submit_capture_is_idempotent_for_duplicate_requests() -> None:
    calls: list[tuple[str, str, str, float]] = []
    service = WebNoteCaptureService(
        project_users=[
            {"username": "CreativeDirector", "token": "tok-creative", "enabled": True},
        ],
        capture_timestamp_fn=lambda: 12.5,
        create_note_marker_fn=lambda username, note_type, body, pos_sec: calls.append((username, note_type, body, pos_sec)) or {"ok": True},
    )

    capture = service.create_capture("tok-creative", "General")
    first = service.submit_capture("tok-creative", capture["capture_id"], "Hold here")
    second = service.submit_capture("tok-creative", capture["capture_id"], "Hold here")

    assert calls == [("CreativeDirector", "General", "Hold here", 12.5)]
    assert first == second
