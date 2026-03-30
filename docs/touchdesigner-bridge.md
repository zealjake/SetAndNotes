# TouchDesigner TCP Bridge

This bridge is the simplest practical way to let TouchDesigner exchange state and commands with SetAndNotes without adding third-party dependencies.

It uses:

- a small TCP server in Python
- newline-delimited JSON messages
- polling from TouchDesigner

## Python Side

Bridge server module:

- [bridge_server.py](/Users/jake/Documents/dev/SetAndNotes/src/setandnotes/touchdesigner/bridge_server.py)

Core objects:

- `TouchDesignerBridge`
- `TouchDesignerBridgeServer`

The bridge stores:

- the latest TouchDesigner state payload
- a FIFO queue of commands for TouchDesigner to run

## Message Types

### TouchDesigner -> server: state update

```json
{
  "type": "state_update",
  "payload": {
    "status": "idle",
    "tc": "01:00:00:00",
    "recording": false
  }
}
```

Response:

```json
{
  "ok": true
}
```

### TouchDesigner -> server: poll for commands

```json
{
  "type": "poll"
}
```

Response:

```json
{
  "ok": true,
  "commands": [
    {
      "action": "start_recording",
      "payload": {
        "session_name": "BandRehearsal"
      }
    }
  ],
  "state": {
    "status": "ready",
    "tc": "01:10:00:00"
  }
}
```

## Recommended First Command Set

Start with only these actions:

- `start_recording`
- `stop_recording`
- `add_marker`
- `refresh_state`

That is enough to coordinate with the capture controller.

## Minimal Python Runner

You can start a bridge from a plain Python shell like this:

```python
from setandnotes.touchdesigner.bridge_server import TouchDesignerBridge, TouchDesignerBridgeServer

bridge = TouchDesignerBridge()
server = TouchDesignerBridgeServer(("127.0.0.1", 9988), bridge)
server.start()

bridge.enqueue_command("refresh_state")
```

## TouchDesigner Side

Inside TouchDesigner, the easiest first client is a `Text DAT` helper that opens a TCP socket, sends JSON, and reads one response.

Use this as a starting point in a DAT such as:

- `/project1/rehearsal_capture/bridge_client`

```python
import json
import socket


HOST = "127.0.0.1"
PORT = 9988


def send_bridge_message(message):
    payload = (json.dumps(message) + "\\n").encode("utf-8")
    with socket.create_connection((HOST, PORT), timeout=1.0) as client:
        client.sendall(payload)
        response = client.recv(8192).decode("utf-8").strip()
    return json.loads(response) if response else {}


def send_state_update(status, tc, recording):
    return send_bridge_message(
        {
            "type": "state_update",
            "payload": {
                "status": status,
                "tc": tc,
                "recording": recording,
            },
        }
    )


def poll_commands():
    return send_bridge_message({"type": "poll"})
```

## Recommended TD Poll Loop

For v1:

- send state every 500ms to 1000ms
- poll commands every 500ms to 1000ms
- when a command arrives, call your controller extension methods

Pseudo-flow:

```python
reply = mod.bridge_client.poll_commands()
for command in reply.get("commands", []):
    action = command["action"]
    payload = command.get("payload", {})

    if action == "start_recording":
        parent().ext.RehearsalCaptureExt.StartRecording()
    elif action == "stop_recording":
        parent().ext.RehearsalCaptureExt.StopRecording()
    elif action == "add_marker":
        parent().ext.RehearsalCaptureExt.AddMarker(payload.get("song_name", "Marker"))
```

## Why TCP Instead Of OSC

For this project, TCP is the better first bridge because:

- no extra dependency is required
- payloads can be structured JSON
- debugging is easier
- state and commands can use the same channel

## Next Integration Step

Once the TouchDesigner patch shell exists, the next useful step is:

1. run the Python bridge locally
2. add the TouchDesigner `bridge_client` DAT
3. make one manual state update call from TouchDesigner
4. make one manual poll call from TouchDesigner
5. only then wire it into the controller buttons or pulse loop
