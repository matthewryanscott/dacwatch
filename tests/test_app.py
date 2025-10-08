import pytest
import asyncio
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dacwatch.app import DaCWatchApp
from dacwatch.config import Config


@pytest.mark.asyncio
async def test_app_initialization(tmp_path):
    """Test app initializes correctly."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directory=directory)

    app = DaCWatchApp(config)

    assert app.config == config
    assert app.is_running is False


@pytest.mark.asyncio
async def test_app_start_stop(tmp_path):
    """Test app can start and stop."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directory=directory)

    app = DaCWatchApp(config)

    # Start the app
    await app.start()
    assert app.is_running is True

    # Stop the app
    await app.stop()
    assert app.is_running is False


@pytest.mark.asyncio
async def test_app_run_with_timeout(tmp_path):
    """Test app run method with timeout."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directory=directory)

    app = DaCWatchApp(config)

    # Start the app manually to check state
    await app.start()
    assert app.is_running is True

    # Create a task and cancel it after a short time
    task = asyncio.create_task(app.run())
    await asyncio.sleep(0.05)  # Let it run briefly
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass

    # App should be stopped after cancellation
    assert app.is_running is False


@pytest.mark.asyncio
async def test_qapplication_initialization_no_existing_instance(tmp_path):
    """Test QApplication initialization when no instance exists."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directory=directory)

    with patch('dacwatch.app.QApplication') as mock_qapp_class:
        mock_qapp_instance = MagicMock()
        mock_qapp_class.instance.return_value = None
        mock_qapp_class.return_value = mock_qapp_instance

        app = DaCWatchApp(config)
        await app.start()

        # Verify QApplication was created
        mock_qapp_class.assert_called_once_with([])
        assert app.qt_app == mock_qapp_instance


@pytest.mark.asyncio
async def test_qapplication_initialization_existing_instance(tmp_path):
    """Test QApplication initialization when instance already exists."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directory=directory)

    with patch('dacwatch.app.QApplication') as mock_qapp_class:
        from PySide6.QtWidgets import QApplication
        # Use real QApplication instance for proper Qt type checking
        real_qapp = QApplication.instance()
        mock_qapp_class.instance.return_value = real_qapp

        app = DaCWatchApp(config)
        await app.start()

        # Verify QApplication was not created again
        mock_qapp_class.assert_not_called()
        assert app.qt_app is None  # Should remain None when instance exists


@pytest.mark.asyncio
async def test_start_without_preregistering_files(tmp_path):
    """Test that app starts without creating windows for existing files."""
    directory = tmp_path / "test_dir"
    directory.mkdir()

    # Create some existing diagram files
    (directory / "test1.dot").write_text("digraph G { A -> B; }")
    (directory / "test2.puml").write_text("@startuml\nA -> B\n@enduml")

    config = Config(directory=directory)
    app = DaCWatchApp(config)

    # Mock the window manager to track if windows are created during start
    with patch('dacwatch.app.WindowManager') as mock_wm_class:
        mock_wm_instance = MagicMock()
        mock_wm_class.return_value = mock_wm_instance

        await app.start()

        # Verify no windows were created for existing files during startup
        mock_wm_instance.get_or_create_window.assert_not_called()
        mock_wm_instance.create_window.assert_not_called()

        await app.stop()


@pytest.mark.asyncio
async def test_qapplication_cleanup_on_stop(tmp_path):
    """Test QApplication cleanup when app stops."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directory=directory)

    with patch('dacwatch.app.QApplication') as mock_qapp_class:
        mock_qapp_instance = MagicMock()
        mock_qapp_class.instance.return_value = None
        mock_qapp_class.return_value = mock_qapp_instance

        app = DaCWatchApp(config)
        await app.start()
        await app.stop()

        # Verify app state is cleaned up
        assert app.is_running is False
        # Note: qt_app should still be set after stop for potential reuse