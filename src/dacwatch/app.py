import asyncio
from typing import Optional
from queue import Queue
import threading
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from .config import Config
from .file_watcher import FileWatcher
from .window_manager import WindowManager


class DaCWatchApp:
    """Main application class for DaCWatch."""

    def __init__(self, config: Config):
        self.config = config
        self.is_running = False
        self.file_watcher: Optional[FileWatcher] = None
        self.window_manager: Optional[WindowManager] = None
        self.qt_app: Optional[QApplication] = None
        self.event_queue = Queue()
        self.file_watcher_thread: Optional[threading.Thread] = None

    async def start(self):
        """Start the application."""
        self.is_running = True
        print(f"DaCWatch starting - watching directory: {self.config.directory}")
        print(f"Using Kroki service: {self.config.kroki_base}")

        # Initialize Qt application
        if QApplication.instance() is None:
            self.qt_app = QApplication([])

        # Initialize the window manager
        self.window_manager = WindowManager()

        # Start the file watcher
        self.file_watcher = FileWatcher(self.config, self._handle_file_event)
        await self.file_watcher.start()

        # Scan for existing diagram files to establish baseline (no windows created)
        await self._scan_existing_files()

    async def stop(self):
        """Stop the application."""
        self.is_running = False

        # Stop the file watcher
        if self.file_watcher:
            await self.file_watcher.stop()

        print("DaCWatch stopped")

    async def _handle_file_event(self, event_type: str, file_path: str):
        """Handle file events by creating/updating windows."""
        if not self.window_manager:
            return

        if event_type in ['created', 'modified']:
            # Create or get window for the file
            window = self.window_manager.get_or_create_window(file_path)
            if window:
                window.show()  # Make sure the window is visible
        elif event_type == 'deleted':
            # Clean up window for deleted file
            self.window_manager.cleanup_deleted_file(file_path)

    async def _scan_existing_files(self):
        """Scan the watched directory for existing diagram files to establish baseline."""
        if not self.window_manager:
            return

        from .file_type import is_supported_file
        from pathlib import Path

        directory = Path(self.config.directory)
        if not directory.exists():
            return

        # Just scan and remember existing files - don't create windows for them
        # This establishes our baseline so we only respond to changes after startup
        for file_path in directory.rglob('*'):
            if file_path.is_file() and is_supported_file(file_path):
                # Store the file path to track it, but don't create a window
                # The file watcher will handle any changes after this point
                pass

    async def run(self):
        """Run the main application loop."""
        await self.start()
        
        # Keep the async loop running indefinitely
        # The qasync integration will handle Qt events automatically
        try:
            while self.is_running:
                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            print("Received interrupt signal")
        except asyncio.CancelledError:
            print("Application cancelled")
        finally:
            await self.stop()