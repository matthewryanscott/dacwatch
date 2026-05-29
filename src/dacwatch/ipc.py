"""Single-instance IPC transport for DaCWatch.

A running DaCWatch instance listens on a Unix-domain socket in ``~/.dacwatch/``.
The CLI uses this module to hand resolved paths to that running instance (or to
detect that none is running so it can launch one). The protocol is a single
connection per invocation: the client writes newline-separated absolute path
strings (UTF-8) then closes the write end; the server reads to EOF.
"""

import socket
import time
from pathlib import Path

# The ~/.dacwatch/ directory is already used for window_state.json
# (see WindowManager._get_default_state_file_path).
DACWATCH_DIR = Path.home() / ".dacwatch"
SOCKET_PATH = DACWATCH_DIR / "dacwatch.sock"
SERVER_LOG_PATH = DACWATCH_DIR / "server.log"


def _encode_paths(paths: list[str]) -> bytes:
    """Encode a list of paths into the wire format (newline-separated UTF-8)."""
    return "\n".join(paths).encode("utf-8")


def decode_paths(data: bytes) -> list[str]:
    """Decode the wire format back into a list of paths, dropping blanks."""
    return [line for line in data.decode("utf-8").splitlines() if line.strip()]


def try_send_to_running_instance(paths: list[str]) -> bool:
    """Send paths to an already-running instance.

    Returns True if a live instance accepted the message. Returns False if no
    instance is running; a stale socket file (left behind by a dead process) is
    unlinked so the caller can launch a fresh server.
    """
    if not SOCKET_PATH.exists():
        return False

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(str(SOCKET_PATH))
        sock.sendall(_encode_paths(paths))
        return True
    except (ConnectionRefusedError, FileNotFoundError, OSError):
        # Stale socket — the owning process is gone. Remove it so a launch can
        # bind a fresh one.
        try:
            SOCKET_PATH.unlink()
        except FileNotFoundError:
            pass
        return False
    finally:
        sock.close()


def wait_for_socket(timeout: float = 15.0) -> bool:
    """Poll until the socket is actually connectable (not just present).

    Used after launching a detached server to know when it is ready to receive.
    Returns True once a connection succeeds, False if the timeout elapses.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if SOCKET_PATH.exists():
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.connect(str(SOCKET_PATH))
                return True
            except (ConnectionRefusedError, FileNotFoundError, OSError):
                pass
            finally:
                sock.close()
        time.sleep(0.1)
    return False
