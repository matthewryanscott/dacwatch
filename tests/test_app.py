import pytest
import asyncio
from pathlib import Path
import sys

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