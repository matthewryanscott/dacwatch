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