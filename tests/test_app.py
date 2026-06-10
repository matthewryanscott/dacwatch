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
    config = Config(directories=[directory])

    app = DaCWatchApp(config)

    assert app.config == config
    assert app.is_running is False


@pytest.mark.asyncio
async def test_app_start_stop(tmp_path):
    """Test app can start and stop."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

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
    config = Config(directories=[directory])

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
    config = Config(directories=[directory])

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
    config = Config(directories=[directory])

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

    config = Config(directories=[directory])
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
    config = Config(directories=[directory])

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


@pytest.mark.asyncio
async def test_handle_markdown_event_created(tmp_path):
    """Test that markdown file creates windows for each diagram block."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    # Create a markdown file with two diagram blocks
    md_file = directory / "test.md"
    md_file.write_text(
        "# Doc\n\n"
        "```plantuml\n@startuml\nA -> B\n@enduml\n```\n\n"
        "```mermaid\ngraph TD\n  A --> B\n```\n"
    )

    app = DaCWatchApp(config)
    await app.start()

    # Mock kroki client to return fake image data
    mock_kroki = MagicMock()

    async def fake_render(source, dtype, fmt="svg"):
        return b'<svg>test</svg>'

    mock_kroki.render_diagram = fake_render
    app.kroki_client = mock_kroki

    # Mock window manager
    mock_wm = MagicMock()
    mock_window = MagicMock()
    mock_wm.get_or_create_window.return_value = mock_window
    app.window_manager = mock_wm

    await app._handle_file_event('created', str(md_file))

    # Should have called get_or_create_window for each diagram block
    assert mock_wm.get_or_create_window.call_count == 2

    # Check first call
    first_call = mock_wm.get_or_create_window.call_args_list[0]
    assert first_call[0][0] == f"{md_file}:0"
    assert first_call[1]['actual_file_path'] == str(md_file)

    # Check second call
    second_call = mock_wm.get_or_create_window.call_args_list[1]
    assert second_call[0][0] == f"{md_file}:1"

    # Cleanup stale windows should have been called
    mock_wm.cleanup_stale_markdown_windows.assert_called_once_with(str(md_file), 2)

    await app.stop()


@pytest.mark.asyncio
async def test_handle_markdown_event_deleted(tmp_path):
    """Test that deleting a markdown file closes all its windows."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    app = DaCWatchApp(config)
    await app.start()

    # Mock window manager
    mock_wm = MagicMock()
    app.window_manager = mock_wm
    app.kroki_client = MagicMock()

    md_path = str(directory / "test.md")
    await app._handle_file_event('deleted', md_path)

    mock_wm.cleanup_markdown_windows.assert_called_once_with(md_path)

    await app.stop()


@pytest.mark.asyncio
async def test_handle_diagram_event_still_works(tmp_path):
    """Test that regular diagram files still work after markdown changes."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    dot_file = directory / "test.dot"
    dot_file.write_text("digraph G { A -> B; }")

    app = DaCWatchApp(config)
    await app.start()

    # Mock kroki client
    mock_kroki = MagicMock()

    async def fake_render(source, dtype, fmt="svg"):
        return b'<svg>test</svg>'

    mock_kroki.render_diagram = fake_render
    mock_kroki.get_diagram_type.return_value = "graphviz"
    app.kroki_client = mock_kroki

    # Mock window manager
    mock_wm = MagicMock()
    mock_window = MagicMock()
    mock_wm.get_or_create_window.return_value = mock_window
    app.window_manager = mock_wm

    await app._handle_file_event('created', str(dot_file))

    # Should use regular get_or_create_window (no actual_file_path)
    mock_wm.get_or_create_window.assert_called_once_with(str(dot_file))

    await app.stop()


@pytest.mark.asyncio
async def test_handle_markdown_no_diagram_blocks(tmp_path):
    """Test markdown file with no diagram blocks creates no windows."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    md_file = directory / "test.md"
    md_file.write_text(
        "# Just text\n\n"
        "```python\nprint('hello')\n```\n"
    )

    app = DaCWatchApp(config)
    await app.start()

    mock_wm = MagicMock()
    app.window_manager = mock_wm
    app.kroki_client = MagicMock()

    await app._handle_file_event('created', str(md_file))

    mock_wm.get_or_create_window.assert_not_called()
    mock_wm.cleanup_stale_markdown_windows.assert_called_once_with(str(md_file), 0)

    await app.stop()


@pytest.mark.asyncio
async def test_render_markdown_block_format_toggle(tmp_path):
    """Test format toggle for markdown diagram block."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    md_file = directory / "test.md"
    md_file.write_text(
        "```plantuml\n@startuml\nA -> B\n@enduml\n```\n"
    )

    app = DaCWatchApp(config)
    await app.start()

    mock_kroki = MagicMock()

    async def fake_render(source, dtype, fmt="svg"):
        return b'<svg>png</svg>'

    mock_kroki.render_diagram = fake_render
    app.kroki_client = mock_kroki

    mock_window = MagicMock()

    await app._render_markdown_block(str(md_file), 0, mock_window, "png")

    # Window should have display_image called
    mock_window.display_image.assert_called_once()
    assert mock_window.source_code == "@startuml\nA -> B\n@enduml\n"

    await app.stop()


@pytest.mark.asyncio
async def test_render_markdown_block_removed(tmp_path):
    """Test format toggle when block has been removed."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    config = Config(directories=[directory])

    md_file = directory / "test.md"
    md_file.write_text("# No diagrams\n")

    app = DaCWatchApp(config)
    await app.start()
    app.kroki_client = MagicMock()

    mock_window = MagicMock()

    await app._render_markdown_block(str(md_file), 0, mock_window, "svg")

    mock_window.display_error.assert_called_once()

    await app.stop()

@pytest.mark.asyncio
async def test_add_watch_path_file_renders_immediately(tmp_path):
    """Adding a file watches it and renders it right away."""
    directory = tmp_path / "d"
    directory.mkdir()
    config = Config(directories=[directory])
    app = DaCWatchApp(config)

    app.file_watcher = MagicMock()

    mock_kroki = MagicMock()

    async def fake_render(source, dtype, fmt="svg"):
        return b'<svg>test</svg>'

    mock_kroki.render_diagram = fake_render
    mock_kroki.get_diagram_type.return_value = "graphviz"
    app.kroki_client = mock_kroki

    mock_wm = MagicMock()
    mock_wm.get_or_create_window.return_value = MagicMock()
    app.window_manager = mock_wm

    dot = directory / "g.dot"
    dot.write_text("digraph { a -> b }")

    await app.add_watch_path(str(dot))

    app.file_watcher.add_file.assert_called_once()
    app.file_watcher.add_directory.assert_not_called()
    mock_wm.get_or_create_window.assert_called_once_with(str(dot.resolve()))


@pytest.mark.asyncio
async def test_add_watch_path_directory_defers_render(tmp_path):
    """Adding a directory registers the watch but renders nothing yet."""
    directory = tmp_path / "d"
    directory.mkdir()
    config = Config(directories=[directory])
    app = DaCWatchApp(config)

    app.file_watcher = MagicMock()
    app.kroki_client = MagicMock()
    mock_wm = MagicMock()
    app.window_manager = mock_wm

    extra = tmp_path / "extra"
    extra.mkdir()

    await app.add_watch_path(str(extra))

    app.file_watcher.add_directory.assert_called_once()
    app.file_watcher.add_file.assert_not_called()
    mock_wm.get_or_create_window.assert_not_called()


@pytest.mark.asyncio
async def test_remove_watch_path_file_closes_window(tmp_path):
    """Removing a watched file unschedules it and closes its window."""
    directory = tmp_path / "d"
    directory.mkdir()
    config = Config(directories=[directory])
    app = DaCWatchApp(config)

    app.file_watcher = MagicMock()
    mock_wm = MagicMock()
    app.window_manager = mock_wm

    dot = (directory / "g.dot")
    dot.write_text("digraph { a -> b }")
    resolved = str(dot.resolve())

    app.remove_watch_path(resolved, "file")

    app.file_watcher.remove_file.assert_called_once()
    mock_wm.cleanup_deleted_file.assert_called_once_with(resolved)


def test_present_window_activate_false_only_shows():
    """activate=False shows the window without raising/activating it."""
    win = MagicMock()
    DaCWatchApp._present_window(win, activate=False)
    win.show.assert_called_once()
    win.raise_.assert_not_called()
    win.activateWindow.assert_not_called()


def test_present_window_activate_true_foregrounds():
    """activate=True shows, raises, and activates the window."""
    win = MagicMock()
    DaCWatchApp._present_window(win, activate=True)
    win.show.assert_called_once()
    win.raise_.assert_called_once()
    win.activateWindow.assert_called_once()


@pytest.mark.asyncio
async def test_diagram_foregrounds_only_on_first_render(tmp_path):
    """First render foregrounds the app; re-renders update in place quietly."""
    directory = tmp_path / "d"
    directory.mkdir()
    dot = directory / "g.dot"
    dot.write_text("digraph { a -> b }")
    config = Config(directories=[directory])
    app = DaCWatchApp(config)

    mock_kroki = MagicMock()

    async def fake_render(source, dtype, fmt="svg"):
        return b"<svg/>"

    mock_kroki.render_diagram = fake_render
    mock_kroki.get_diagram_type.return_value = "graphviz"
    app.kroki_client = mock_kroki

    win = MagicMock()
    mock_wm = MagicMock()
    mock_wm.get_or_create_window.return_value = win
    app.window_manager = mock_wm
    app._present_window = MagicMock()

    # First render: no existing window -> foreground.
    mock_wm.get_window_for_file.return_value = None
    await app._handle_file_event("created", str(dot))
    assert app._present_window.call_args.kwargs.get("activate") is True

    # Re-render (e.g. save while editing): window exists -> no foreground.
    mock_wm.get_window_for_file.return_value = win
    app._present_window.reset_mock()
    await app._handle_file_event("modified", str(dot))
    assert app._present_window.call_args.kwargs.get("activate") is False


def _make_app_with_mock_render(tmp_path, render_impl, default_format="svg"):
    """Build a DaCWatchApp with a mocked kroki client and window manager."""
    directory = tmp_path / "d"
    directory.mkdir()
    config = Config(directories=[directory])
    app = DaCWatchApp(config)

    mock_kroki = MagicMock()
    mock_kroki.render_diagram = render_impl
    app.kroki_client = mock_kroki

    win = MagicMock()
    mock_wm = MagicMock()
    mock_wm.get_or_create_window.return_value = win
    mock_wm.get_window_for_file.return_value = win
    app.window_manager = mock_wm
    app._present_window = MagicMock()
    return app, mock_wm, win


@pytest.mark.asyncio
async def test_clipboard_paste_detects_and_renders(tmp_path):
    """Pasting mermaid source detects the type and displays the image."""
    from dacwatch.kroki_client import KrokiError

    async def fake_render(source, dtype, fmt="svg"):
        if dtype == "mermaid":
            return b"PNGDATA"
        raise KrokiError(400, "Bad", "nope")

    app, mock_wm, win = _make_app_with_mock_render(tmp_path, fake_render)

    await app._handle_clipboard_paste("flowchart TD\n A-->B")

    # New window keyed clipboard:1 with a mermaid title, foregrounded.
    args, kwargs = mock_wm.get_or_create_window.call_args
    assert args[0] == "clipboard:1"
    assert "mermaid" in kwargs["window_title"]
    win.display_image.assert_called_once_with(b"PNGDATA", "png")
    assert win.source_code == "flowchart TD\n A-->B"
    assert app._present_window.call_args.kwargs.get("activate") is True


@pytest.mark.asyncio
async def test_clipboard_paste_increments_counter(tmp_path):
    """Each paste opens a new window keyed clipboard:N."""
    async def fake_render(source, dtype, fmt="svg"):
        return b"DATA"

    app, mock_wm, win = _make_app_with_mock_render(tmp_path, fake_render)

    await app._handle_clipboard_paste("flowchart TD\n A-->B")
    await app._handle_clipboard_paste("flowchart TD\n C-->D")

    keys = [c.args[0] for c in mock_wm.get_or_create_window.call_args_list]
    assert keys == ["clipboard:1", "clipboard:2"]


@pytest.mark.asyncio
async def test_clipboard_paste_no_type_match_shows_error(tmp_path):
    """When no candidate type renders, an error window is shown."""
    from dacwatch.kroki_client import KrokiError

    async def fake_render(source, dtype, fmt="svg"):
        raise KrokiError(400, "Bad", "syntax error")

    app, mock_wm, win = _make_app_with_mock_render(tmp_path, fake_render)

    await app._handle_clipboard_paste("not a real diagram")

    win.display_error.assert_called_once()
    assert "detect" in win.display_error.call_args.args[0].lower()
    win.display_image.assert_not_called()


@pytest.mark.asyncio
async def test_clipboard_paste_network_error_shows_error(tmp_path):
    """A non-400 Kroki error surfaces as an error window, not a crash."""
    from dacwatch.kroki_client import KrokiError

    async def fake_render(source, dtype, fmt="svg"):
        raise KrokiError(502, "Bad Gateway", "upstream down")

    app, mock_wm, win = _make_app_with_mock_render(tmp_path, fake_render)

    await app._handle_clipboard_paste("flowchart TD\n A-->B")

    win.display_error.assert_called_once()
    win.display_image.assert_not_called()


def test_paste_from_clipboard_empty_is_noop(tmp_path):
    """An empty clipboard beeps and does not spawn a paste task."""
    directory = tmp_path / "d"
    directory.mkdir()
    config = Config(directories=[directory])
    app = DaCWatchApp(config)

    with patch("dacwatch.app.read_text_from_clipboard", return_value="   "), \
            patch("asyncio.create_task") as mock_create_task:
        app._paste_diagram_from_clipboard()
        mock_create_task.assert_not_called()


def test_paste_from_clipboard_spawns_task(tmp_path, qapp):
    """Non-empty clipboard text spawns the async paste handler."""
    directory = tmp_path / "d"
    directory.mkdir()
    config = Config(directories=[directory])
    app = DaCWatchApp(config)

    with patch("dacwatch.app.read_text_from_clipboard", return_value="flowchart TD\n A-->B"), \
            patch("asyncio.create_task") as mock_create_task:
        app._paste_diagram_from_clipboard()
        mock_create_task.assert_called_once()
        # Close the unawaited coroutine handed to the mocked create_task.
        mock_create_task.call_args.args[0].close()


def test_setup_menu_has_paste_action(tmp_path, qapp):
    """The persistent menu bar exposes a Cmd+Shift+V paste action."""
    from PySide6.QtGui import QAction

    directory = tmp_path / "d"
    directory.mkdir()
    app = DaCWatchApp(Config(directories=[directory]))
    app._setup_menu()

    paste = next(
        (a for a in app._menu_bar.findChildren(QAction)
         if a.text() == "Paste Diagram from Clipboard"),
        None,
    )
    assert paste is not None
    assert paste.shortcut().toString() == "Ctrl+V"
