from typing import Dict, List, Optional, Any, Callable
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
        self.loading_label: Optional[QLabel] = None
        self.format_label: Optional[QLabel] = None
        self.format_toggle_callback: Optional[Callable[[str], None]] = None
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

        # Setup toolbar
        self._setup_toolbar()

    def display_image(self, image_data: bytes, format: str):
        """
        Display rendered diagram image in the window using QScrollArea.

        Args:
            image_data: The image data as bytes
            format: Image format ("svg" or "png")

        Raises:
            ValueError: If format is not supported
        """
        if format not in ["svg", "png"]:
            raise ValueError("Format must be 'svg' or 'png'")

        from PySide6.QtWidgets import QLabel, QScrollArea
        from PySide6.QtGui import QPixmap, QPainter
        from PySide6.QtCore import QByteArray, QSize
        from PySide6.QtSvg import QSvgRenderer

        # Create image label
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Get device pixel ratio for high-DPI displays
        device_pixel_ratio = self.devicePixelRatio()

        # Create pixmap from image data with high-DPI support
        if format == "svg":
            # For SVG, use QSvgRenderer for high-quality rendering
            byte_array = QByteArray(image_data)
            svg_renderer = QSvgRenderer(byte_array)
            
            if svg_renderer.isValid():
                # Get default size or use fallback
                default_size = svg_renderer.defaultSize()
                if default_size.isEmpty() or default_size.width() <= 0 or default_size.height() <= 0:
                    default_size = QSize(800, 600)
                
                # Render at high resolution for crisp display
                display_width = int(default_size.width() * device_pixel_ratio)
                display_height = int(default_size.height() * device_pixel_ratio)
                
                pixmap = QPixmap(display_width, display_height)
                pixmap.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                svg_renderer.render(painter)
                painter.end()
                
                pixmap.setDevicePixelRatio(device_pixel_ratio)
            else:
                pixmap = QPixmap()
        else:  # PNG
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            pixmap.setDevicePixelRatio(device_pixel_ratio)
        
        # Set pixmap on label
        image_label.setPixmap(pixmap)
        
        # Create scroll area to contain the image
        scroll_area = QScrollArea()
        scroll_area.setWidget(image_label)
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Update format label
        if self.format_label:
            self.format_label.setText(f"Format: {format.upper()}")
            self.format_label.show()

        # Replace loading label or existing image with scroll area
        central_widget = self.centralWidget()
        if central_widget:
            layout = central_widget.layout()
            if layout:
                # Remove loading label on first display
                if self.loading_label and self.loading_label.isVisible():
                    layout.removeWidget(self.loading_label)
                    self.loading_label.hide()
                
                # Remove existing scroll area if present
                if hasattr(self, 'scroll_area') and self.scroll_area is not None:
                    try:
                        layout.removeWidget(self.scroll_area)
                        self.scroll_area.deleteLater()
                    except (RuntimeError, AttributeError):
                        pass
                
                # Add new scroll area
                layout.addWidget(scroll_area)

        # Store references
        self.scroll_area = scroll_area
        self.image_label = image_label
        
        # Store image data for format toggling
        self.image_data = image_data
        self.current_format = format

    def _setup_toolbar(self):
        """Setup the toolbar with action buttons."""
        from PySide6.QtWidgets import QToolBar, QPushButton
        from PySide6.QtCore import Qt

        # Create toolbar
        toolbar = QToolBar("Diagram Actions")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        # Toggle format button
        self.toggle_button = QPushButton("Toggle SVG/PNG")
        self.toggle_button.clicked.connect(self.toggle_format)
        toolbar.addWidget(self.toggle_button)

        # Copy image button
        self.copy_image_button = QPushButton("Copy Image")
        self.copy_image_button.clicked.connect(self.copy_image_to_clipboard)
        toolbar.addWidget(self.copy_image_button)

        # Copy source button
        self.copy_source_button = QPushButton("Copy Source")
        self.copy_source_button.clicked.connect(self.copy_source_to_clipboard)
        toolbar.addWidget(self.copy_source_button)

        # Reveal in Finder button
        self.reveal_button = QPushButton("Reveal in Finder")
        self.reveal_button.clicked.connect(self.reveal_in_finder)
        toolbar.addWidget(self.reveal_button)

        # Create format label for toolbar
        from PySide6.QtWidgets import QLabel
        self.format_label = QLabel("")
        self.format_label.setStyleSheet("color: gray; font-size: 12px; padding: 5px;")
        toolbar.addWidget(self.format_label)

        # Store current format and image data
        self.current_format = "svg"  # Default to SVG
        self.image_data = None

    def toggle_format(self):
        """Toggle between SVG and PNG formats."""
        if not hasattr(self, 'image_data') or self.image_data is None:
            return

        # Toggle format
        new_format = "png" if self.current_format == "svg" else "svg"
        
        # We need to re-render with the new format, not just re-display
        # This will be handled by the app when it connects to this signal
        if hasattr(self, 'format_toggle_callback') and self.format_toggle_callback:
            self.format_toggle_callback(new_format)

    def copy_image_to_clipboard(self):
        """Copy the current image to clipboard."""
        if not hasattr(self, 'image_data') or self.image_data is None:
            return

        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QPixmap, QImage
        from PySide6.QtCore import QBuffer, QIODevice, QByteArray

        # Create pixmap from current image data
        pixmap = QPixmap()
        if self.current_format == "svg":
            byte_array = QByteArray(self.image_data)
            pixmap.loadFromData(byte_array)
        else:
            pixmap.loadFromData(self.image_data)

        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setImage(pixmap.toImage())

    def copy_source_to_clipboard(self):
        """Copy the source code to clipboard."""
        try:
            with open(self.file_path, 'r') as f:
                source_code = f.read()

            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(source_code)
        except (IOError, OSError):
            # If we can't read the file, just continue
            pass

    def reveal_in_finder(self):
        """Reveal the file in Finder (macOS)."""
        import subprocess
        try:
            subprocess.run(['open', '-R', self.file_path])
        except (subprocess.SubprocessError, OSError):
            # If subprocess fails, just continue
            pass


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