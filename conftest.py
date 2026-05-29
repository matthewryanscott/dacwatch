"""Pytest configuration for Qt testing."""

import os
import pytest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer


# Set up headless Qt testing
@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create a QApplication instance for testing."""
    # Set up headless mode
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    
    # Create QApplication if it doesn't exist
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    yield app
    
    # Clean up
    if app:
        app.quit()


@pytest.fixture
def qtbot(qapp, request):
    """Provide a qtbot for widget testing."""
    from pytestqt.qtbot import QtBot

    bot = QtBot(request)
    return bot


@pytest.fixture(autouse=True)
def isolate_ipc_socket(monkeypatch):
    """Redirect the IPC socket/log into a short-pathed per-test tmp dir.

    Prevents the test suite from binding (and unlinking) the real
    ~/.dacwatch/dacwatch.sock, which would clobber a developer's running app.
    Uses a short base (/tmp) because AF_UNIX socket paths are capped at ~104
    chars — pytest's deep tmp_path would overflow it.
    """
    import shutil
    import tempfile
    from pathlib import Path

    from dacwatch import ipc

    base = "/tmp" if os.path.isdir("/tmp") else None
    dac_dir = Path(tempfile.mkdtemp(prefix="dacw_", dir=base))
    monkeypatch.setattr(ipc, "DACWATCH_DIR", dac_dir)
    monkeypatch.setattr(ipc, "SOCKET_PATH", dac_dir / "s.sock")
    monkeypatch.setattr(ipc, "SERVER_LOG_PATH", dac_dir / "server.log")
    yield
    shutil.rmtree(dac_dir, ignore_errors=True)