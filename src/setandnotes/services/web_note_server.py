from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any
from urllib.parse import urlparse

from setandnotes.services.web_note_capture import WebNoteCaptureError
from setandnotes.web.web_notes_page import render_web_notes_page


class WebNoteServer:
    def __init__(self, *, capture_service, host: str = "0.0.0.0") -> None:
        self.capture_service = capture_service
        self._server = ThreadingHTTPServer((host, 0), self._make_handler())
        self._thread: Thread | None = None

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _make_handler(self):
        capture_service = self.capture_service

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path.startswith("/notes/u/"):
                    user_key = parsed.path.rsplit("/", 1)[-1]
                    user = _find_user(capture_service.project_users, user_key)
                    if user is None or not bool(user.get("enabled", True)):
                        self._json_response(404, {"error": "Unknown web note user"})
                        return
                    body = render_web_notes_page(username=str(user["username"]), token=str(user["token"]))
                    encoded = body.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)
                    return

                self._json_response(404, {"error": "Not found"})

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                try:
                    payload = json.loads(raw or "{}")
                except json.JSONDecodeError:
                    self._json_response(400, {"error": "Invalid JSON payload"})
                    return

                try:
                    if self.path == "/api/web-notes/capture":
                        response = capture_service.create_capture(payload["token"], payload["note_type"])
                        self._json_response(200, response)
                        return
                    if self.path == "/api/web-notes/submit":
                        if not str(payload["body"]).strip():
                            raise WebNoteCaptureError("Note body is required")
                        response = capture_service.submit_capture(payload["token"], payload["capture_id"], payload["body"])
                        self._json_response(200, response)
                        return
                except KeyError as exc:
                    self._json_response(400, {"error": f"Missing field: {exc.args[0]}"})
                    return
                except WebNoteCaptureError as exc:
                    self._json_response(400, {"error": str(exc)})
                    return

                self._json_response(404, {"error": "Not found"})

            def log_message(self, format: str, *args: Any) -> None:
                return None

            def _json_response(self, status: int, payload: dict[str, Any]) -> None:
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        return Handler


def _find_user(project_users: list[dict[str, Any]], user_key: str) -> dict[str, Any] | None:
    for user in project_users:
        if user.get("slug") == user_key or user.get("token") == user_key:
            return user
    return None
