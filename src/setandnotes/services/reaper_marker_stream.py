from __future__ import annotations

import json
import socket
import threading
from collections.abc import Callable


def parse_marker_event_line(line: str) -> list[dict] | None:
    line = line.strip()
    prefix = "EVENT MARKERS "
    if not line.startswith(prefix):
        return None
    return json.loads(line[len(prefix) :])


class ReaperMarkerStreamClient:
    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 28731,
        timeout: float = 2.0,
        socket_factory: Callable[[str, int, float], socket.socket] | None = None,
        on_markers: Callable[[list[dict]], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket_factory = socket_factory or _default_socket_factory
        self.on_markers = on_markers
        self.on_error = on_error
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _run_forever(self) -> None:
        while not self._stop_event.is_set():
            self._run_once()
            if self._stop_event.wait(1.0):
                return

    def _run_once(self) -> None:
        try:
            sock = self.socket_factory(self.host, self.port, self.timeout)
        except OSError:
            if self.on_error is not None:
                self.on_error("Unable to connect to REAPER marker stream")
            return

        try:
            sock.sendall(b"RS_SUBSCRIBE_MARKERS\n")
            buffer = ""
            while not self._stop_event.is_set():
                chunk = sock.recv(4096)
                if not chunk:
                    return
                buffer += chunk.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    markers = parse_marker_event_line(line)
                    if markers is not None and self.on_markers is not None:
                        self.on_markers(markers)
        except OSError:
            if self.on_error is not None:
                self.on_error("REAPER marker stream disconnected")
        finally:
            sock.close()


def _default_socket_factory(host: str, port: int, timeout: float) -> socket.socket:
    return socket.create_connection((host, port), timeout=timeout)
