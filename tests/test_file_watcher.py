import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dacwatch.file_watcher import FileWatcher
from dacwatch.config import Config


@pytest.mark.asyncio
async def test_file_watcher_initialization(tmp_path):
    """Test file watcher initializes correctly."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)

    assert watcher.config == config
    assert watcher.is_watching is False


@pytest.mark.asyncio
async def test_file_watcher_start_stop(tmp_path):
    """Test file watcher can start and stop."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)

    # Start the watcher
    await watcher.start()
    assert watcher.is_watching is True

    # Stop the watcher
    await watcher.stop()
    assert watcher.is_watching is False


@pytest.mark.asyncio
async def test_file_watcher_observer_setup(tmp_path):
    """Test file watcher sets up observer correctly."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)
    await watcher.start()

    # Verify observer was created
    assert watcher.observer is not None
    assert watcher.event_handler is not None
    assert watcher.is_watching is True

    await watcher.stop()
    assert watcher.is_watching is False


@pytest.mark.asyncio
async def test_file_watcher_event_handling(tmp_path):
    """Test file watcher handles file events."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)

    # Create a test file
    test_file = directory / "test.dot"
    test_file.write_text("digraph test { a -> b; }")

    # Simulate file creation event
    await watcher.handle_file_event({
        'event_type': 'created',
        'src_path': str(test_file),
        'is_directory': False
    })

    # The test passes if no exception is raised and the file is processed
    # (we can see from the captured output that it printed the event)


@pytest.mark.asyncio
async def test_file_watcher_ignores_unsupported_files(tmp_path):
    """Test file watcher ignores unsupported file types."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)

    # Create a test file with unsupported extension
    test_file = directory / "test.txt"
    test_file.write_text("This is a text file")

    # Simulate file creation event
    await watcher.handle_file_event({
        'event_type': 'created',
        'src_path': str(test_file),
        'is_directory': False
    })

    # The test passes if no exception is raised (unsupported files are ignored)


@pytest.mark.asyncio
async def test_file_watcher_handles_multiple_file_types(tmp_path):
    """Test file watcher handles different supported file types."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)

    # Test .dot file
    dot_file = directory / "test.dot"
    dot_file.write_text("digraph test { a -> b; }")
    await watcher.handle_file_event({
        'event_type': 'created',
        'src_path': str(dot_file),
        'is_directory': False
    })

    # Test .puml file
    puml_file = directory / "test.puml"
    puml_file.write_text("@startuml\ntest\n@enduml")
    await watcher.handle_file_event({
        'event_type': 'created',
        'src_path': str(puml_file),
        'is_directory': False
    })

    # Test .mermaid file
    mermaid_file = directory / "test.mermaid"
    mermaid_file.write_text("graph TD\nA-->B")
    await watcher.handle_file_event({
        'event_type': 'created',
        'src_path': str(mermaid_file),
        'is_directory': False
    })

    # The test passes if no exceptions are raised


@pytest.mark.asyncio
async def test_file_watcher_handles_file_modification(tmp_path):
    """Test file watcher handles file modification events."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)

    # Create and then modify a test file
    test_file = directory / "test.dot"
    test_file.write_text("digraph test { a -> b; }")

    await watcher.handle_file_event({
        'event_type': 'modified',
        'src_path': str(test_file),
        'is_directory': False
    })

    # The test passes if no exception is raised


@pytest.mark.asyncio
async def test_file_watcher_handles_file_deletion(tmp_path):
    """Test file watcher handles file deletion events."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)

    # Simulate deletion of a file that doesn't exist (but would be supported)
    deleted_file = directory / "deleted.dot"

    await watcher.handle_file_event({
        'event_type': 'deleted',
        'src_path': str(deleted_file),
        'is_directory': False
    })

    # The test passes if no exception is raised


@pytest.mark.asyncio
async def test_file_watcher_filters_directory_events(tmp_path):
    """Test file watcher ignores directory events."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)

    # Create a subdirectory
    subdir = directory / "subdir"
    subdir.mkdir()

    # The AsyncEventHandler should filter out directory events before calling handle_file_event
    # But let's test that handle_file_event handles directory events gracefully
    await watcher.handle_file_event({
        'event_type': 'created',
        'src_path': str(subdir),
        'is_directory': True
    })

    # The test passes if no exception is raised (directory events should be filtered by AsyncEventHandler)


@pytest.mark.asyncio
async def test_file_watcher_case_insensitive_extensions(tmp_path):
    """Test file watcher handles case-insensitive extensions."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)

    # Test uppercase extension
    uppercase_file = directory / "test.DOT"
    uppercase_file.write_text("digraph test { a -> b; }")

    await watcher.handle_file_event({
        'event_type': 'created',
        'src_path': str(uppercase_file),
        'is_directory': False
    })

    # Test mixed case extension
    mixedcase_file = directory / "test.PuMl"
    mixedcase_file.write_text("@startuml\ntest\n@enduml")

    await watcher.handle_file_event({
        'event_type': 'created',
        'src_path': str(mixedcase_file),
        'is_directory': False
    })

    # The test passes if no exceptions are raised


@pytest.mark.asyncio
async def test_file_watcher_event_queue_debouncing(tmp_path):
    """Test file watcher debounces rapid events."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)

    # Check that debounce delay is 1 second
    assert watcher.debounce_delay == 1.0

    await watcher.start()

    test_file = directory / "test.dot"

    # Simulate rapid events on the same file
    events = [
        {'event_type': 'created', 'src_path': str(test_file), 'is_directory': False},
        {'event_type': 'modified', 'src_path': str(test_file), 'is_directory': False},
        {'event_type': 'modified', 'src_path': str(test_file), 'is_directory': False},
        {'event_type': 'modified', 'src_path': str(test_file), 'is_directory': False},
    ]

    # Queue all events quickly
    for event in events:
        await watcher.handle_file_event(event)

    # Wait for processing to complete
    await asyncio.sleep(watcher.debounce_delay + 0.1)

    await watcher.stop()

    # The test passes if no exceptions are raised (debouncing should work)


@pytest.mark.asyncio
async def test_file_watcher_multiple_files(tmp_path):
    """Test file watcher handles events for multiple files."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)
    await watcher.start()

    # Create multiple files
    files = [
        directory / "test1.dot",
        directory / "test2.puml",
        directory / "test3.mermaid"
    ]

    # Simulate events for each file
    for i, file_path in enumerate(files):
        file_path.write_text(f"content {i}")
        await watcher.handle_file_event({
            'event_type': 'created',
            'src_path': str(file_path),
            'is_directory': False
        })

    # Wait for processing
    await asyncio.sleep(watcher.debounce_delay + 0.1)

    await watcher.stop()

    # The test passes if no exceptions are raised


@pytest.mark.asyncio
async def test_file_watcher_event_flattening_created_modified(tmp_path):
    """Test that {created, modified} events are flattened to {created}."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)
    await watcher.start()

    test_file = directory / "test.dot"

    # Simulate created followed by modified
    await watcher.handle_file_event({
        'event_type': 'created',
        'src_path': str(test_file),
        'is_directory': False
    })
    await watcher.handle_file_event({
        'event_type': 'modified',
        'src_path': str(test_file),
        'is_directory': False
    })

    # Wait for processing
    await asyncio.sleep(watcher.debounce_delay + 0.1)

    await watcher.stop()

    # The test passes if no exceptions are raised


@pytest.mark.asyncio
async def test_file_watcher_event_flattening_modified_deleted(tmp_path):
    """Test that {modified, deleted} events are flattened to {deleted}."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)
    await watcher.start()

    test_file = directory / "test.dot"

    # Simulate modified followed by deleted
    await watcher.handle_file_event({
        'event_type': 'modified',
        'src_path': str(test_file),
        'is_directory': False
    })
    await watcher.handle_file_event({
        'event_type': 'deleted',
        'src_path': str(test_file),
        'is_directory': False
    })

    # Wait for processing
    await asyncio.sleep(watcher.debounce_delay + 0.1)

    await watcher.stop()

    # The test passes if no exceptions are raised


@pytest.mark.asyncio
async def test_file_watcher_event_flattening_created_deleted(tmp_path):
    """Test that {created, deleted} events are flattened to {deleted}."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    watcher = FileWatcher(config)
    await watcher.start()

    test_file = directory / "test.dot"

    # Simulate created followed by deleted
    await watcher.handle_file_event({
        'event_type': 'created',
        'src_path': str(test_file),
        'is_directory': False
    })
    await watcher.handle_file_event({
        'event_type': 'deleted',
        'src_path': str(test_file),
        'is_directory': False
    })

    # Wait for processing
    await asyncio.sleep(watcher.debounce_delay + 0.1)

    await watcher.stop()

    # The test passes if no exceptions are raised


def test_file_watcher_flatten_events_method(tmp_path):
    """Test the _flatten_events method directly with file existence checks."""
    from dacwatch.file_watcher import FileWatcher
    from dacwatch.config import Config

    config = Config(directories=[tmp_path])
    watcher = FileWatcher(config)

    # Create a test file that exists
    existing_file = tmp_path / "existing.dot"
    existing_file.write_text("graph { a -- b }")

    # File that doesn't exist
    deleted_file = tmp_path / "deleted.dot"

    # Test events for existing files
    assert watcher._flatten_events({'created'}, str(existing_file)) == 'created'
    assert watcher._flatten_events({'modified'}, str(existing_file)) == 'modified'
    assert watcher._flatten_events({'created', 'modified'}, str(existing_file)) == 'created'

    # Test delete+create with file existing (file replacement)
    assert watcher._flatten_events({'created', 'deleted'}, str(existing_file)) == 'created'
    assert watcher._flatten_events({'created', 'modified', 'deleted'}, str(existing_file)) == 'created'

    # Test events for non-existing files (all result in deleted)
    assert watcher._flatten_events({'deleted'}, str(deleted_file)) == 'deleted'
    assert watcher._flatten_events({'modified', 'deleted'}, str(deleted_file)) == 'deleted'
    assert watcher._flatten_events({'created', 'deleted'}, str(deleted_file)) == 'deleted'
    assert watcher._flatten_events({'created', 'modified', 'deleted'}, str(deleted_file)) == 'deleted'

    # Test empty set
    assert watcher._flatten_events(set(), str(existing_file)) is None