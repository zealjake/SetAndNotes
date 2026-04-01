from __future__ import annotations

import http.client
import json

from setandnotes.services.web_note_capture import WebNoteCaptureError


class _FakeCaptureService:
    def __init__(self) -> None:
        self.project_users = [
            {"username": "CreativeDirector", "token": "tok-creative", "slug": "creative-director", "enabled": True},
            {"username": "VideoDirector", "token": "tok-video", "slug": "video-director", "enabled": False},
        ]
        self.capture_calls: list[tuple[str, str]] = []
        self.submit_calls: list[tuple[str, str, str]] = []

    def create_capture(self, token: str, note_type: str) -> dict:
        self.capture_calls.append((token, note_type))
        if token == "missing":
            raise WebNoteCaptureError("Unknown web note user")
        return {"capture_id": "cap-1", "username": "CreativeDirector", "note_type": note_type, "playhead_sec": 12.0}

    def submit_capture(self, token: str, capture_id: str, body: str) -> dict:
        self.submit_calls.append((token, capture_id, body))
        return {"capture_id": capture_id, "username": "CreativeDirector", "note_type": "General", "playhead_sec": 12.0}


def test_get_token_page_shows_fixed_username_and_buttons():
    from setandnotes.services.web_note_server import WebNoteServer

    service = _FakeCaptureService()
    server = WebNoteServer(capture_service=service)
    server.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=2)
        conn.request("GET", "/notes/u/creative-director")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        conn.close()
    finally:
        server.stop()

    assert response.status == 200
    assert "CreativeDirector" in body
    assert "General" in body
    assert "Lighting" in body
    assert "Content" in body
    assert "Cameras" in body
    assert "username" not in body.lower()
    assert "/api/web-notes/capture" in body
    assert "/api/web-notes/submit" in body


def test_capture_endpoint_returns_capture_id():
    from setandnotes.services.web_note_server import WebNoteServer

    service = _FakeCaptureService()
    server = WebNoteServer(capture_service=service)
    server.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=2)
        conn.request(
            "POST",
            "/api/web-notes/capture",
            body=json.dumps({"token": "tok-creative", "note_type": "Content"}),
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        conn.close()
    finally:
        server.stop()

    assert response.status == 200
    assert payload["capture_id"] == "cap-1"
    assert service.capture_calls == [("tok-creative", "Content")]


def test_submit_endpoint_creates_note_from_capture_id():
    from setandnotes.services.web_note_server import WebNoteServer

    service = _FakeCaptureService()
    server = WebNoteServer(capture_service=service)
    server.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=2)
        conn.request(
            "POST",
            "/api/web-notes/submit",
            body=json.dumps({"token": "tok-creative", "capture_id": "cap-1", "body": "Hold here"}),
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        conn.close()
    finally:
        server.stop()

    assert response.status == 200
    assert payload["capture_id"] == "cap-1"
    assert service.submit_calls == [("tok-creative", "cap-1", "Hold here")]


def test_unknown_token_is_rejected():
    from setandnotes.services.web_note_server import WebNoteServer

    service = _FakeCaptureService()
    server = WebNoteServer(capture_service=service)
    server.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=2)
        conn.request(
            "POST",
            "/api/web-notes/capture",
            body=json.dumps({"token": "missing", "note_type": "General"}),
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        conn.close()
    finally:
        server.stop()

    assert response.status == 400
    assert payload["error"] == "Unknown web note user"


def test_legacy_token_route_still_works():
    from setandnotes.services.web_note_server import WebNoteServer

    service = _FakeCaptureService()
    server = WebNoteServer(capture_service=service)
    server.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=2)
        conn.request("GET", "/notes/u/tok-creative")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        conn.close()
    finally:
        server.stop()

    assert response.status == 200
    assert "CreativeDirector" in body


def test_blank_note_submit_returns_validation_error():
    from setandnotes.services.web_note_server import WebNoteServer

    service = _FakeCaptureService()
    server = WebNoteServer(capture_service=service)
    server.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=2)
        conn.request(
            "POST",
            "/api/web-notes/submit",
            body=json.dumps({"token": "tok-creative", "capture_id": "cap-1", "body": "   "}),
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        conn.close()
    finally:
        server.stop()

    assert response.status == 400
    assert payload["error"] == "Note body is required"
