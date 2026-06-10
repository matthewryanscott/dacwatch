import asyncio
import logging
from typing import Optional
from queue import Queue
import threading
import aiohttp
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from pathlib import Path
from . import ipc
from .clipboard import read_text_from_clipboard
from .config import Config
from .diagram_detect import detect_and_render, ordered_candidates
from .file_type import is_supported_file
from .file_watcher import FileWatcher
from .ipc import decode_paths
from .window_manager import WindowManager
from .kroki_client import KrokiClient, KrokiError
from .markdown_parser import is_markdown_file, extract_diagram_blocks
from .watched_paths_window import WatchedPathsWindow

logger = logging.getLogger(__name__)

# Diagram types whose SVG uses <foreignObject> (unsupported by Qt's QSvgRenderer)
_PNG_DEFAULT_TYPES = frozenset({"mermaid"})


class DaCWatchApp:
    """Main application class for DaCWatch."""

    def __init__(self, config: Config):
        self.config = config
        self.is_running = False
        self.file_watcher: Optional[FileWatcher] = None
        self.window_manager: Optional[WindowManager] = None
        self.kroki_client: Optional[KrokiClient] = None
        self.qt_app: Optional[QApplication] = None
        self.event_queue = Queue()
        self.file_watcher_thread: Optional[threading.Thread] = None
        self.ipc_server: Optional[asyncio.AbstractServer] = None
        self.watched_paths_window: Optional[WatchedPathsWindow] = None
        # Monotonic counter for clipboard-pasted diagrams; each paste gets its
        # own window keyed "clipboard:N".
        self._clipboard_counter = 0
        # Persistent, parentless menu bar so the Window menu stays reachable on
        # macOS even when no diagram windows are open.
        self._menu_bar = None

    async def start(self):
        """Start the application."""
        self.is_running = True
        dirs = ", ".join(str(d) for d in self.config.directories)
        logger.info("DaCWatch starting - watching directories: %s", dirs)
        logger.info("Using Kroki service: %s", self.config.kroki_base)

        # Initialize Qt application with high-DPI support
        if QApplication.instance() is None:
            # Enable high-DPI support before creating QApplication
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
            self.qt_app = QApplication([])

        # Initialize the window manager
        self.window_manager = WindowManager()

        # Initialize the Kroki client
        self.kroki_client = KrokiClient(self.config.kroki_base)

        # Setup application-level keyboard shortcuts
        self._setup_app_shortcuts()

        # Persistent Window menu (reachable with no windows open on macOS)
        self._setup_menu()

        # Let the window manager open the Watched Paths window from its menus
        self.window_manager.on_open_watched_paths = self._open_watched_paths_window

        # Let diagram windows trigger a clipboard paste from their Window menu.
        self.window_manager.on_paste_diagram = self._paste_diagram_from_clipboard

        # Start the file watcher
        self.file_watcher = FileWatcher(self.config, self._handle_file_event)
        await self.file_watcher.start()

        # Start the single-instance IPC server so other CLI invocations can hand
        # us their paths.
        await self._start_ipc_server()

    def _setup_app_shortcuts(self):
        """Setup application-level keyboard shortcuts."""
        from PySide6.QtGui import QShortcut, QKeySequence
        from PySide6.QtCore import Qt

        # Get the QApplication instance
        app = QApplication.instance()
        if not app:
            return

        # Cycle windows forward (Cmd+Shift+] / Cmd+})
        cycle_forward = QShortcut(QKeySequence("Ctrl+Shift+]"), app)
        cycle_forward.setContext(Qt.ShortcutContext.ApplicationShortcut)
        cycle_forward.activated.connect(lambda: self._cycle_windows(False))

        # Cycle windows backward (Cmd+Shift+[ / Cmd+{)
        cycle_backward = QShortcut(QKeySequence("Ctrl+Shift+["), app)
        cycle_backward.setContext(Qt.ShortcutContext.ApplicationShortcut)
        cycle_backward.activated.connect(lambda: self._cycle_windows(True))

    def _cycle_windows(self, backward=False):
        """Cycle through windows."""
        if self.window_manager:
            self.window_manager.cycle_to_next_window(backward=backward)

    # ------------------------------------------------------------------
    # Single-instance IPC
    # ------------------------------------------------------------------

    async def _start_ipc_server(self):
        """Listen on the Unix socket for paths sent by other CLI invocations.

        Runs on the qasync/Qt loop, so the client handler can touch widgets and
        the window manager directly without a thread bridge.
        """
        socket_path = ipc.SOCKET_PATH
        socket_path.parent.mkdir(parents=True, exist_ok=True)
        # Remove any stale socket left by a previous (dead) instance.
        try:
            socket_path.unlink()
        except FileNotFoundError:
            pass
        self.ipc_server = await asyncio.start_unix_server(
            self._handle_ipc_client, path=str(socket_path)
        )
        logger.info("IPC server listening on %s", socket_path)

    async def _handle_ipc_client(self, reader, writer):
        """Read newline-separated paths from a client and add each watch."""
        try:
            data = await reader.read()
            for raw in decode_paths(data):
                await self.add_watch_path(raw)
        except Exception:
            logger.exception("Error handling IPC client message")
        finally:
            writer.close()

    async def add_watch_path(self, raw_path: str):
        """Add a directory or file to the live watcher.

        Directories register a recursive watch and render only on later changes;
        files render immediately and then keep watching.
        """
        if not self.file_watcher:
            return
        path = Path(raw_path).resolve()
        if path.is_dir():
            self.file_watcher.add_directory(path)
            logger.info("Now watching directory: %s", path)
        elif path.is_file() and is_supported_file(path):
            self.file_watcher.add_file(path)
            logger.info("Now watching file: %s", path)
            # Render the existing file immediately (reuses the change-event path,
            # including markdown handling).
            await self._handle_file_event("created", str(path))
        else:
            logger.warning("Ignoring unwatchable path: %s", path)
            return
        self._refresh_watched_paths_window()

    def remove_watch_path(self, raw_path: str, kind: str):
        """Stop watching a path (called from the Watched Paths window)."""
        if not self.file_watcher:
            return
        path = Path(raw_path).resolve()
        if kind == "directory":
            self.file_watcher.remove_directory(path)
        else:
            self.file_watcher.remove_file(path)
            if self.window_manager:
                self.window_manager.cleanup_deleted_file(str(path))
        logger.info("Stopped watching: %s", path)
        self._refresh_watched_paths_window()

    # ------------------------------------------------------------------
    # Window menu + Watched Paths window
    # ------------------------------------------------------------------

    def _setup_menu(self):
        """Create a persistent parentless menu bar with a Window menu.

        On macOS this keeps the Window menu in the global menu bar even when no
        diagram windows are open, so the Watched Paths window stays reachable.
        """
        from PySide6.QtGui import QAction, QKeySequence
        from PySide6.QtWidgets import QMenuBar

        self._menu_bar = QMenuBar()
        window_menu = self._menu_bar.addMenu("Window")

        paste_action = QAction("Paste Diagram from Clipboard", self._menu_bar)
        paste_action.setShortcut(QKeySequence("Ctrl+V"))
        paste_action.triggered.connect(self._paste_diagram_from_clipboard)
        window_menu.addAction(paste_action)

        action = QAction("Watched Paths…", self._menu_bar)
        action.setShortcut(QKeySequence("Ctrl+Shift+P"))
        action.triggered.connect(self._open_watched_paths_window)
        window_menu.addAction(action)

    @staticmethod
    def _present_window(window, activate: bool = True):
        """Show a window, optionally bringing it (and the app) to the front.

        With activate=True the window is raised and activated — used for a
        diagram's first render so the app surfaces. With activate=False the
        window is only shown (content updates in place), so re-renders from file
        watching don't steal focus while you edit the source.
        """
        if not activate:
            window.show()
            return

        from PySide6.QtCore import Qt

        # Clear a possible minimized state so the window actually appears.
        window.setWindowState(
            (window.windowState() & ~Qt.WindowState.WindowMinimized)
            | Qt.WindowState.WindowActive
        )
        window.show()
        window.raise_()
        window.activateWindow()

    def _open_watched_paths_window(self):
        """Open (or focus) the Watched Paths window."""
        if self.watched_paths_window is None:
            self.watched_paths_window = WatchedPathsWindow(self)
        self._refresh_watched_paths_window()
        self._present_window(self.watched_paths_window)

    def _refresh_watched_paths_window(self):
        """Refresh the Watched Paths window if it exists."""
        if self.watched_paths_window is None or not self.file_watcher:
            return
        self.watched_paths_window.refresh(
            sorted(self.file_watcher.watched_dirs, key=str),
            sorted(self.file_watcher.watched_files, key=str),
        )

    # ------------------------------------------------------------------
    # Clipboard paste
    # ------------------------------------------------------------------

    def _paste_diagram_from_clipboard(self):
        """Render the clipboard's text as a diagram in a new window.

        Triggered by the Cmd+Shift+V menu action. Reads the clipboard, then
        hands off to the async handler that detects the type and renders it.
        """
        source = read_text_from_clipboard()
        if not source or not source.strip():
            logger.info("Paste diagram: clipboard has no text")
            from PySide6.QtWidgets import QApplication
            QApplication.beep()
            return
        asyncio.create_task(self._handle_clipboard_paste(source))

    async def _handle_clipboard_paste(self, source: str):
        """Detect the diagram type of pasted source and render it in a window."""
        if not self.window_manager or not self.kroki_client:
            return

        self._clipboard_counter += 1
        n = self._clipboard_counter
        window_key = f"clipboard:{n}"

        try:
            result = await detect_and_render(
                self.kroki_client, source, self._default_format
            )
        except KrokiError as e:
            window = self._create_clipboard_window(window_key, n, None)
            window.source_code = source
            self._present_window(window, activate=True)
            window.display_error(
                "Rendering error",
                f"Kroki returned status {e.status} while detecting the diagram type.",
                e.body,
            )
            return
        except (aiohttp.ClientError, TimeoutError, OSError) as e:
            window = self._create_clipboard_window(window_key, n, None)
            window.source_code = source
            self._present_window(window, activate=True)
            window.display_error(
                "Network error",
                f"Could not connect to {self.config.kroki_base}",
                str(e),
            )
            return

        if result is None:
            tried = ", ".join(ordered_candidates(source))
            window = self._create_clipboard_window(window_key, n, None)
            window.source_code = source
            self._present_window(window, activate=True)
            window.display_error(
                "Could not detect diagram type",
                f"The clipboard text was not valid as any known type ({tried}).",
                source,
            )
            return

        diagram_type, fmt, image_data = result
        window = self._create_clipboard_window(window_key, n, diagram_type)
        self._present_window(window, activate=True)

        # We already have the rendered image from detection; display it directly
        # and wire up the format toggle to re-render from the known type/source.
        window.source_code = source
        window.image_data = image_data
        window.current_format = fmt
        window.format_toggle_callback = self._make_clipboard_format_callback(
            source, diagram_type, window_key
        )
        try:
            window.display_image(image_data, fmt)
        except Exception:
            logger.exception("Error displaying pasted diagram %s", window_key)

    def _create_clipboard_window(self, window_key: str, n: int, diagram_type: Optional[str]):
        """Create a window for a pasted diagram with a friendly title."""
        suffix = f" ({diagram_type})" if diagram_type else ""
        title = f"DaCWatch - Clipboard {n}{suffix}"
        return self.window_manager.get_or_create_window(
            window_key, window_title=title
        )

    def _make_clipboard_format_callback(self, source: str, diagram_type: str, window_key: str):
        """Build a format-toggle callback that re-renders pasted source."""
        def format_callback(new_format):
            current_window = self.window_manager.get_window_for_file(window_key)
            if current_window:
                asyncio.create_task(
                    self._render_and_display(source, diagram_type, current_window, new_format)
                )
        return format_callback

    async def stop(self):
        """Stop the application."""
        self.is_running = False

        # Stop the IPC server and remove the socket
        if self.ipc_server:
            self.ipc_server.close()
            try:
                await self.ipc_server.wait_closed()
            except Exception:
                pass
            self.ipc_server = None
        try:
            ipc.SOCKET_PATH.unlink()
        except FileNotFoundError:
            pass

        # Stop the file watcher
        if self.file_watcher:
            await self.file_watcher.stop()

        logger.info("DaCWatch stopped")

    async def _handle_file_event(self, event_type: str, file_path: str):
        """Handle file events by creating/updating windows and rendering diagrams."""
        if not self.window_manager or not self.kroki_client:
            return

        if is_markdown_file(Path(file_path)):
            await self._handle_markdown_event(event_type, file_path)
        else:
            await self._handle_diagram_event(event_type, file_path)

    @staticmethod
    def _default_format(diagram_type: str) -> str:
        """Return the default render format for a diagram type."""
        return "png" if diagram_type in _PNG_DEFAULT_TYPES else "svg"

    async def _handle_diagram_event(self, event_type: str, file_path: str):
        """Handle events for regular diagram files (.dot, .puml, .mermaid)."""
        if event_type in ['created', 'modified']:
            # Create or get window for the file. Only foreground the app on the
            # first render (new window); re-renders from file watching update in
            # place without stealing focus while you edit the source.
            is_new = self.window_manager.get_window_for_file(file_path) is None
            window = self.window_manager.get_or_create_window(file_path)
            if window:
                self._present_window(window, activate=is_new)

                # Set up format toggle callback - use a safer approach that doesn't capture window directly
                def create_format_callback(fp, wm):
                    def format_callback(new_format):
                        # Get the current window reference (in case it was recreated)
                        current_window = wm.get_window_for_file(fp)
                        if current_window:
                            asyncio.create_task(
                                self._render_and_display_diagram(fp, current_window, new_format)
                            )
                    return format_callback

                window.format_toggle_callback = create_format_callback(file_path, self.window_manager)

                # Render and display the diagram
                try:
                    await self._render_and_display_diagram(file_path, window)
                except Exception:
                    logger.exception("Error rendering diagram for %s", file_path)

        elif event_type == 'deleted':
            # Clean up window for deleted file
            self.window_manager.cleanup_deleted_file(file_path)

    async def _handle_markdown_event(self, event_type: str, file_path: str):
        """Handle events for markdown files containing diagram code fences."""
        if event_type == 'deleted':
            self.window_manager.cleanup_markdown_windows(file_path)
            return

        # created or modified
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            logger.warning("Markdown file not found: %s", file_path)
            return

        blocks = extract_diagram_blocks(content)

        # Close windows for blocks that no longer exist
        self.window_manager.cleanup_stale_markdown_windows(file_path, len(blocks))

        # Render each diagram block
        md_name = Path(file_path).name
        for block in blocks:
            window_key = f"{file_path}:{block.index}"
            title = f"DaCWatch - {md_name}:{block.index} ({block.diagram_type})"
            # Only foreground when a block's window is first created; re-renders
            # on save update in place without stealing focus.
            is_new = self.window_manager.get_window_for_file(window_key) is None
            window = self.window_manager.get_or_create_window(
                window_key,
                actual_file_path=file_path,
                window_title=title,
            )
            if window:
                self._present_window(window, activate=is_new)

                # Set up format toggle callback for this block
                def create_md_format_callback(fp, idx, wm):
                    def format_callback(new_format):
                        current_window = wm.get_window_for_file(f"{fp}:{idx}")
                        if current_window:
                            asyncio.create_task(
                                self._render_markdown_block(fp, idx, current_window, new_format)
                            )
                    return format_callback

                window.format_toggle_callback = create_md_format_callback(file_path, block.index, self.window_manager)

                try:
                    fmt = self._default_format(block.diagram_type)
                    await self._render_and_display(block.source, block.diagram_type, window, fmt)
                except Exception:
                    logger.exception(
                        "Error rendering markdown block %s from %s",
                        block.index,
                        file_path,
                    )

    async def _render_markdown_block(self, file_path: str, block_index: int, window, format: str = "svg"):
        """Re-read and re-parse a markdown file to render a specific block (for format toggle)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            window.display_error("File not found", f"Could not read file: {file_path}", f"File not found: {file_path}")
            return

        blocks = extract_diagram_blocks(content)
        if block_index >= len(blocks):
            window.display_error("Block removed", f"Diagram block {block_index} no longer exists in {file_path}")
            return

        block = blocks[block_index]
        await self._render_and_display(block.source, block.diagram_type, window, format)

    async def _render_and_display_diagram(self, file_path: str, window, format: str | None = None):
        """Read a diagram file and render it in the window."""
        if not self.kroki_client:
            logger.warning("Kroki client not available")
            return

        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # Determine diagram type
            diagram_type = self.kroki_client.get_diagram_type(file_path)
            if not diagram_type:
                logger.warning("Unsupported file type for %s", file_path)
                return

            if format is None:
                format = self._default_format(diagram_type)

            await self._render_and_display(source_code, diagram_type, window, format)

        except FileNotFoundError:
            logger.warning("File not found: %s", file_path)
            window.display_error("File not found", f"Could not read file: {file_path}", f"File not found: {file_path}")

    async def _render_and_display(self, source: str, diagram_type: str, window, format: str = "svg"):
        """Render diagram source and display it in the window."""
        if not self.kroki_client:
            return

        try:
            image_data = await self.kroki_client.render_diagram(source, diagram_type, format)
            window.image_data = image_data
            window.source_code = source
            window.current_format = format
            window.display_image(image_data, format)

        except KrokiError as e:
            if e.status == 400:
                window.display_error("Diagram syntax error",
                    "The diagram contains invalid syntax.", e.body)
            elif e.status >= 500:
                window.display_error("Server error",
                    "The Kroki service encountered an error.", e.body)
            else:
                window.display_error("Rendering error",
                    f"Kroki returned status {e.status}.", e.body)

        except (aiohttp.ClientError, TimeoutError, OSError) as e:
            window.display_error("Network error",
                f"Could not connect to {self.config.kroki_base}", str(e))

        except Exception as e:
            import traceback
            window.display_error("Rendering error",
                "Unexpected error occurred.", traceback.format_exc())



    async def run(self):
        """Run the main application loop."""
        await self.start()
        
        # Keep the async loop running indefinitely
        # The qasync integration will handle Qt events automatically
        try:
            while self.is_running:
                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except asyncio.CancelledError:
            logger.info("Application cancelled")
        finally:
            await self.stop()