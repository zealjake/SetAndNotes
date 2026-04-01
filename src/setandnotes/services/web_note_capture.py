from __future__ import annotations

import secrets
from dataclasses import dataclass
from threading import Lock
from time import time
from typing import Any, Callable

from setandnotes.services.reaper_notes import capture_note_timestamp, create_note_marker


class WebNoteCaptureError(Exception):
    pass


@dataclass(slots=True)
class PendingCapture:
    capture_id: str
    token: str
    username: str
    note_type: str
    playhead_sec: float
    created_at: float


class WebNoteCaptureService:
    def __init__(
        self,
        *,
        project_users: list[dict[str, Any]],
        capture_timestamp_fn: Callable[[], float] = capture_note_timestamp,
        create_note_marker_fn: Callable[[str, str, str, float], dict] = create_note_marker,
    ) -> None:
        self.project_users = project_users
        self.capture_timestamp_fn = capture_timestamp_fn
        self.create_note_marker_fn = create_note_marker_fn
        self._captures: dict[str, PendingCapture] = {}
        self._submitted: dict[str, dict[str, Any]] = {}
        self._submitting: set[str] = set()
        self._lock = Lock()

    def create_capture(self, token: str, note_type: str) -> dict[str, Any]:
        user = self._user_for_token(token)
        playhead_sec = self.capture_timestamp_fn()
        capture_id = secrets.token_urlsafe(18)
        capture = PendingCapture(
            capture_id=capture_id,
            token=token,
            username=str(user["username"]),
            note_type=note_type,
            playhead_sec=playhead_sec,
            created_at=time(),
        )
        with self._lock:
            self._captures[capture_id] = capture
        return {
            "capture_id": capture.capture_id,
            "username": capture.username,
            "note_type": capture.note_type,
            "playhead_sec": capture.playhead_sec,
        }

    def submit_capture(self, token: str, capture_id: str, body: str) -> dict[str, Any]:
        self._user_for_token(token)
        normalized_body = body.strip()
        if not normalized_body:
            raise WebNoteCaptureError("Note body is required")
        with self._lock:
            submitted = self._submitted.get(capture_id)
            if submitted is not None and submitted.get("token") == token:
                return dict(submitted["result"])
            if capture_id in self._submitting:
                raise WebNoteCaptureError("Capture is already being submitted")
            capture = self._captures.get(capture_id)
            if capture is None or capture.token != token:
                raise WebNoteCaptureError("Unknown or expired capture")
            self._submitting.add(capture_id)

        try:
            self.create_note_marker_fn(capture.username, capture.note_type, normalized_body, capture.playhead_sec)
        except Exception:
            with self._lock:
                self._submitting.discard(capture_id)
            raise

        result = {
            "capture_id": capture.capture_id,
            "username": capture.username,
            "note_type": capture.note_type,
            "playhead_sec": capture.playhead_sec,
        }
        with self._lock:
            self._captures.pop(capture_id, None)
            self._submitting.discard(capture_id)
            self._submitted[capture_id] = {"token": token, "result": dict(result)}
        return result

    def _user_for_token(self, token: str) -> dict[str, Any]:
        for user in self.project_users:
            if user.get("token") != token:
                continue
            if not bool(user.get("enabled", True)):
                raise WebNoteCaptureError("Web note user is disabled")
            return user
        raise WebNoteCaptureError("Unknown web note user")
