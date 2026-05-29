import asyncio
import sys
from pathlib import Path

import pytest

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dacwatch import ipc


def test_send_returns_false_when_no_socket():
    """With no socket file present, there is no running instance."""
    assert not ipc.SOCKET_PATH.exists()
    assert ipc.try_send_to_running_instance(["/some/path"]) is False


def test_send_unlinks_stale_socket():
    """A leftover socket file from a dead process is removed."""
    # A plain file standing in for a stale socket: connecting to it fails.
    ipc.SOCKET_PATH.write_text("")
    assert ipc.SOCKET_PATH.exists()

    assert ipc.try_send_to_running_instance(["/some/path"]) is False
    assert not ipc.SOCKET_PATH.exists()


def test_encode_decode_roundtrip():
    paths = ["/a/b", "/c d/e", "/f"]
    assert ipc.decode_paths(ipc._encode_paths(paths)) == paths


def test_decode_drops_blank_lines():
    assert ipc.decode_paths(b"/a\n\n/b\n   \n") == ["/a", "/b"]


@pytest.mark.asyncio
async def test_send_to_running_instance_roundtrip():
    """A live unix server receives the newline-joined paths."""
    received: list[bytes] = []

    async def handle(reader, writer):
        received.append(await reader.read())
        writer.close()

    server = await asyncio.start_unix_server(handle, path=str(ipc.SOCKET_PATH))
    try:
        paths = ["/abs/one.dot", "/abs/two.puml"]
        # try_send_* is blocking — run it off the event loop thread.
        ok = await asyncio.get_running_loop().run_in_executor(
            None, ipc.try_send_to_running_instance, paths
        )
        assert ok is True
        # Give the server a moment to read the message.
        for _ in range(50):
            if received:
                break
            await asyncio.sleep(0.01)
        assert ipc.decode_paths(received[0]) == paths
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_wait_for_socket():
    """wait_for_socket returns True once a server is connectable."""
    # Not connectable yet.
    assert ipc.wait_for_socket(timeout=0.2) is False

    async def handle(reader, writer):
        writer.close()

    server = await asyncio.start_unix_server(handle, path=str(ipc.SOCKET_PATH))
    try:
        ok = await asyncio.get_running_loop().run_in_executor(
            None, ipc.wait_for_socket, 2.0
        )
        assert ok is True
    finally:
        server.close()
        await server.wait_closed()
