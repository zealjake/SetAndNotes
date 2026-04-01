from __future__ import annotations

from setandnotes.services.reaper_marker_stream import (
    ReaperMarkerStreamClient,
    parse_marker_event_line,
)


def test_parse_marker_event_line_returns_markers_for_event_snapshot() -> None:
    markers = parse_marker_event_line(
        'EVENT MARKERS [{"guid":"song-1","name":"Song 1","pos_sec":1.0,"color_raw":0}]'
    )

    assert markers == [{"guid": "song-1", "name": "Song 1", "pos_sec": 1.0, "color_raw": 0}]


def test_parse_marker_event_line_ignores_non_event_lines() -> None:
    assert parse_marker_event_line("OK SUBSCRIBED") is None


def test_stream_client_subscribes_and_delivers_marker_snapshot() -> None:
    seen: list[list[dict]] = []

    class FakeSocket:
        def __init__(self) -> None:
            self.sent: list[bytes] = []
            self.chunks = iter(
                [
                    b"OK SUBSCRIBED\n",
                    b'EVENT MARKERS [{"guid":"song-1","name":"Song 1","pos_sec":1.0,"color_raw":0}]\n',
                    b"",
                ]
            )

        def sendall(self, payload: bytes) -> None:
            self.sent.append(payload)

        def recv(self, size: int) -> bytes:
            return next(self.chunks)

        def close(self) -> None:
            return None

    fake_socket = FakeSocket()

    client = ReaperMarkerStreamClient(
        socket_factory=lambda host, port, timeout: fake_socket,
        on_markers=seen.append,
    )

    client._run_once()

    assert fake_socket.sent == [b"RS_SUBSCRIBE_MARKERS\n"]
    assert seen == [[{"guid": "song-1", "name": "Song 1", "pos_sec": 1.0, "color_raw": 0}]]


def test_stream_client_reports_connection_errors() -> None:
    errors: list[str] = []

    client = ReaperMarkerStreamClient(
        socket_factory=lambda host, port, timeout: (_ for _ in ()).throw(OSError("boom")),
        on_error=errors.append,
    )

    client._run_once()

    assert errors == ["Unable to connect to REAPER marker stream"]
