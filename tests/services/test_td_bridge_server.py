from __future__ import annotations

import json
import socket
from pathlib import Path

from setandnotes.touchdesigner.bridge_server import TouchDesignerBridge, TouchDesignerBridgeServer


def test_bridge_state_update_and_command_poll():
    bridge = TouchDesignerBridge()

    bridge.update_state({"status": "idle", "tc": "01:00:00:00"})
    bridge.enqueue_command("start_recording", {"session_name": "BandRehearsal"})

    assert bridge.latest_state()["status"] == "idle"
    commands = bridge.drain_commands()
    assert commands == [{"action": "start_recording", "payload": {"session_name": "BandRehearsal"}}]
    assert bridge.drain_commands() == []


def test_bridge_server_handles_state_update_and_poll(tmp_path: Path):
    bridge = TouchDesignerBridge()
    server = TouchDesignerBridgeServer(("127.0.0.1", 0), bridge)
    server.start()
    try:
        bridge.enqueue_command("add_marker", {"song_name": "OpeningSong"})
        port = server.port

        with socket.create_connection(("127.0.0.1", port), timeout=2.0) as client:
            client.sendall(
                (json.dumps({"type": "state_update", "payload": {"status": "ready", "tc": "01:10:00:00"}}) + "\n").encode()
            )
            state_reply = client.recv(4096).decode()

        with socket.create_connection(("127.0.0.1", port), timeout=2.0) as client:
            client.sendall((json.dumps({"type": "poll"}) + "\n").encode())
            poll_reply = client.recv(4096).decode()

        state_payload = json.loads(state_reply.strip())
        poll_payload = json.loads(poll_reply.strip())

        assert state_payload["ok"] is True
        assert bridge.latest_state()["tc"] == "01:10:00:00"
        assert poll_payload["commands"][0]["action"] == "add_marker"
    finally:
        server.stop()
