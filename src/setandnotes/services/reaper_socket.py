from __future__ import annotations

import socket


DEFAULT_REAPER_HOST = "127.0.0.1"
DEFAULT_REAPER_PORT = 28731


def send_reaper_command(
    command: str,
    *,
    host: str = DEFAULT_REAPER_HOST,
    port: int = DEFAULT_REAPER_PORT,
    timeout: float = 2.0,
) -> str:
    payload = f"{command}\n".encode("utf-8")
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(payload)
        response = b""
        while not response.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
    return response.decode("utf-8").strip()
