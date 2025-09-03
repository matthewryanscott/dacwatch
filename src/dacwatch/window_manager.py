from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import os

# PySide imports
from PySide6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class DiagramWindow(QMainWindow):
    """A window for displaying diagram files."""

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.loading_label = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        # Set window title
        file_name = Path(self.file_path).name
        self.setWindowTitle(f"DaCWatch - {file_name}")

        # Set window geometry (position and size)
        self.setGeometry(100, 100, 800, 600)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create loading label
        self.loading_label = QLabel("Loading diagram...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loading_label)


class WindowManager:
    """Manages the mapping between files and their corresponding windows."""

    def __init__(self, state_file_path: Optional[str] = None):
        self.windows: Dict[str, Any] = {}  # file_path -> window
        self.window_states: Dict[str, Dict[str, int]] = {}  # file_path -> state
        self.state_file_path = state_file_path or self._get_default_state_file_path()
        self.load_state()

    @property
    def window_count(self) -> int:
        """Get the number of open windows."""
        return len(self.windows)

    def get_window_for_file(self, file_path: str) -> Optional[Any]:
        """
        Get the window for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            The window object if it exists, None otherwise
        """
        return self.windows.get(file_path)

    def create_window(self, file_path: str) -> Any:
        """
        Create a new window for a file.

        Args:
            file_path: Path to the file

        Returns:
            The created window object
        """
        window = self._create_window(file_path)
        self.windows[file_path] = window

        # Restore previous state if available
        self.restore_window_state(window, file_path)

        return window

    def close_window(self, file_path: str):
        """
        Close the window for a specific file.

        Args:
            file_path: Path to the file
        """
        window = self.windows.get(file_path)
        if window:
            # Save window state before closing
            self.save_window_state(file_path)
            window.close()
            del self.windows[file_path]

            # Persist state to disk
            self.persist_state()

    def get_or_create_window(self, file_path: str) -> Any:
        """
        Get existing window for file, or create a new one if it doesn't exist.

        Args:
            file_path: Path to the file

        Returns:
            The window object
        """
        window = self.get_window_for_file(file_path)
        if window is None:
            window = self.create_window(file_path)
        return window

    def list_open_files(self) -> List[str]:
        """
        Get a list of all files that have open windows.

        Returns:
            List of file paths
        """
        return list(self.windows.keys())

    def close_all_windows(self):
        """Close all open windows."""
        for file_path in list(self.windows.keys()):
            self.close_window(file_path)

    def cleanup_deleted_file(self, file_path: str):
        """
        Clean up the window for a deleted file.

        Args:
            file_path: Path to the deleted file
        """
        self.close_window(file_path)

    def cleanup_deleted_files(self, deleted_files: List[str]):
        """
        Clean up windows for multiple deleted files.

        Args:
            deleted_files: List of paths to deleted files
        """
        for file_path in deleted_files:
            self.cleanup_deleted_file(file_path)

    def _get_default_state_file_path(self) -> str:
        """Get the default path for the window state file."""
        home_dir = Path.home()
        return str(home_dir / ".dacwatch" / "window_state.json")

    def save_window_state(self, file_path: str):
        """
        Save the state of a window.

        Args:
            file_path: Path to the file
        """
        window = self.windows.get(file_path)
        if window:
            try:
                # Get window geometry
                x = window.x()
                y = window.y()
                width = window.width()
                height = window.height()

                # Only save if we got actual integer values (not Mocks)
                if all(isinstance(val, int) for val in [x, y, width, height]):
                    self.window_states[file_path] = {
                        'x': x,
                        'y': y,
                        'width': width,
                        'height': height
                    }
            except AttributeError:
                # Window might not have geometry methods (e.g., during testing)
                pass

    def restore_window_state(self, window: Any, file_path: str):
        """
        Restore the state of a window.

        Args:
            window: The window object
            file_path: Path to the file
        """
        state = self.window_states.get(file_path)
        if state:
            try:
                window.setGeometry(
                    state['x'],
                    state['y'],
                    state['width'],
                    state['height']
                )
            except (AttributeError, KeyError):
                # Window might not have setGeometry method or state might be incomplete
                pass

    def persist_state(self):
        """Persist window states to disk."""
        try:
            # Ensure directory exists
            state_dir = Path(self.state_file_path).parent
            state_dir.mkdir(parents=True, exist_ok=True)

            with open(self.state_file_path, 'w') as f:
                json.dump(self.window_states, f, indent=2)
        except (OSError, IOError):
            # If we can't persist state, just continue
            pass

    def load_state(self):
        """Load window states from disk."""
        try:
            if os.path.exists(self.state_file_path):
                with open(self.state_file_path, 'r') as f:
                    self.window_states = json.load(f)
        except (OSError, IOError, json.JSONDecodeError):
            # If we can't load state, start with empty state
            self.window_states = {}

    def _create_window(self, file_path: str) -> DiagramWindow:
        """
        Create a DiagramWindow for a diagram file.

        Args:
            file_path: Path to the diagram file

        Returns:
            A DiagramWindow instance for the diagram
        """
        return DiagramWindow(file_path)