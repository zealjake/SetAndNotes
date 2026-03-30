from __future__ import annotations

import json
import socketserver
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TouchDesignerBridge:
    _state: dict[str, Any] = field(default_factory=dict)
    _commands: list[dict[str, Any]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def update_state(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._state = dict(payload)

    def latest_state(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)

    def enqueue_command(self, action: str, payload: dict[str, Any] | None = None) -> None:
        with self._lock:
            self._commands.append({"action": action, "payload": dict(payload or {})})

    def drain_commands(self) -> list[dict[str, Any]]:
        with self._lock:
            commands = list(self._commands)
            self._commands.clear()
            return commands


class _BridgeTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, server_address, bridge: TouchDesignerBridge):
        self.bridge = bridge
        super().__init__(server_address, _BridgeHandler)


class _BridgeHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw_line = self.rfile.readline()
        if not raw_line:
            return

        try:
            request = json.loads(raw_line.decode("utf-8"))
        except json.JSONDecodeError:
            self._reply({"ok": False, "error": "invalid_json"})
            return

        message_type = request.get("type")
        if message_type == "state_update":
            payload = request.get("payload", {})
            self.server.bridge.update_state(payload)
            self._reply({"ok": True})
            return

        if message_type == "poll":
            self._reply(
                {
                    "ok": True,
                    "commands": self.server.bridge.drain_commands(),
                    "state": self.server.bridge.latest_state(),
                }
            )
            return

        self._reply({"ok": False, "error": "unknown_type"})

    def _reply(self, payload: dict[str, Any]) -> None:
        self.wfile.write((json.dumps(payload) + "\n").encode("utf-8"))


class TouchDesignerBridgeServer:
    def __init__(self, address: tuple[str, int], bridge: TouchDesignerBridge):
        self._server = _BridgeTCPServer(address, bridge)
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
