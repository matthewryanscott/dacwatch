from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import json
import os

# PySide imports
from PySide6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QPainter


class ZoomableGraphicsView(QGraphicsView):
    """A QGraphicsView with zoom and pan capabilities via mouse wheel and gestures."""

    def __init__(self, parent_window=None):
        super().__init__()
        self.parent_window = parent_window
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        # Enable gesture support for pinch-to-zoom
        self.grabGesture(Qt.GestureType.PinchGesture)
        
        # Zoom limits
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.zoom_factor_base = 1.0015

    def wheelEvent(self, event):
        """Handle mouse wheel for scrolling (not zooming)."""
        # Let the default scroll behavior handle wheel events
        super().wheelEvent(event)

    def event(self, event):
        """Handle gesture events for pinch-to-zoom."""
        if event.type() == QEvent.Type.Gesture:
            return self.gestureEvent(event)
        return super().event(event)

    def gestureEvent(self, event):
        """Handle pinch gesture for touch zoom."""
        gesture = event.gesture(Qt.GestureType.PinchGesture)
        if gesture:
            if gesture.state() == Qt.GestureState.GestureUpdated:
                # Get scale factor from pinch gesture
                scale_factor = gesture.scaleFactor()
                
                # Apply zoom with limits
                current_scale = self.transform().m11()
                if (current_scale * scale_factor < self.min_zoom and scale_factor < 1) or \
                   (current_scale * scale_factor > self.max_zoom and scale_factor > 1):
                    return True
                
                self.scale(scale_factor, scale_factor)
                
                # Notify parent window of zoom change if available
                if self.parent_window and hasattr(self.parent_window, 'current_zoom_scale'):
                    self.parent_window.current_zoom_scale = self.get_current_scale()
            return True
        return False

    def fit_in_view_with_margin(self, rect, margin_percent=10, scale_factor=1.0):
        """Fit the given rect in view with a margin and apply a scale factor."""
        if rect.isNull():
            return
            
        # Add margin to the rect
        margin_x = rect.width() * (margin_percent / 100.0)
        margin_y = rect.height() * (margin_percent / 100.0)
        expanded_rect = rect.adjusted(-margin_x, -margin_y, margin_x, margin_y)
        
        # Fit in view first
        self.fitInView(expanded_rect, Qt.AspectRatioMode.KeepAspectRatio)
        
        # Then apply additional scale factor (2x by default for better visibility)
        self.scale(scale_factor, scale_factor)

    def reset_zoom(self):
        """Reset zoom to 1:1 pixel ratio (no scaling)."""
        if self.scene():
            self.resetTransform()  # Reset to 1:1 pixel ratio
            
    def get_current_scale(self):
        """Get the current scale factor."""
        return self.transform().m11()
        
    def set_scale(self, scale_factor):
        """Set absolute scale factor."""
        current_scale = self.get_current_scale()
        if current_scale > 0:
            # Reset transform and apply new scale
            self.resetTransform()
            self.scale(scale_factor, scale_factor)


class DiagramWindow(QMainWindow):
    """A window for displaying diagram files."""

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.loading_label: Optional[QLabel] = None
        self.format_label: Optional[QLabel] = None
        self.format_toggle_callback: Optional[Callable[[str], None]] = None
        self.current_zoom_scale: float = 1.0  # Store current zoom level
        self.is_first_display: bool = True  # Track if this is the first image display
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        # Set window title
        file_name = Path(self.file_path).name
        self.setWindowTitle(f"DaCWatch - {file_name}")

        # Set window flags to stay on top without stealing focus
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

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
        
        # Setup keyboard shortcuts
        self._setup_shortcuts()
        
        # Connect checkbox signal after method is defined
        self.always_on_top_checkbox.toggled.connect(self.toggle_always_on_top)

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

        from PySide6.QtGui import QPixmap, QPainter
        from PySide6.QtCore import QByteArray, QSize
        from PySide6.QtSvg import QSvgRenderer

        # Window will automatically stay on top due to WindowStaysOnTopHint

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
                
                # Render at high resolution for crisp display on high-DPI screens
                display_width = int(default_size.width() * device_pixel_ratio)
                display_height = int(default_size.height() * device_pixel_ratio)
                
                pixmap = QPixmap(display_width, display_height)
                pixmap.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                svg_renderer.render(painter)
                painter.end()
                
                # CRITICAL: Set device pixel ratio so Qt knows this is a high-DPI pixmap
                pixmap.setDevicePixelRatio(device_pixel_ratio)
            else:
                pixmap = QPixmap()
        else:  # PNG
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            pixmap.setDevicePixelRatio(device_pixel_ratio)
        
        # Create graphics view and scene for zoomable display
        graphics_view = ZoomableGraphicsView(parent_window=self)
        graphics_scene = QGraphicsScene()
        
        # Create pixmap item and add to scene
        pixmap_item = QGraphicsPixmapItem(pixmap)
        graphics_scene.addItem(pixmap_item)
        
        # Set scene on view
        graphics_view.setScene(graphics_scene)
        
        # Set white background for the graphics view
        graphics_view.setStyleSheet("QGraphicsView { background-color: white; }")
        
        # Save current zoom before replacing view (only if not first display)
        if not self.is_first_display and hasattr(self, 'graphics_view') and self.graphics_view:
            self.current_zoom_scale = self.graphics_view.get_current_scale()
        
        if self.is_first_display:
            # First time - reset transform for true 1:1 display (no scaling)
            graphics_view.resetTransform()
            self.current_zoom_scale = 1.0
            self.is_first_display = False
        else:
            # Subsequent updates - reset transform first, then apply saved scale
            graphics_view.resetTransform()
            graphics_view.set_scale(self.current_zoom_scale)

        # Update format label
        if self.format_label:
            self.format_label.setText(f"Format: {format.upper()}")
            self.format_label.show()

        # Replace loading label or existing image with graphics view
        central_widget = self.centralWidget()
        if central_widget:
            layout = central_widget.layout()
            if layout:
                # Remove loading label on first display
                if self.loading_label and self.loading_label.isVisible():
                    layout.removeWidget(self.loading_label)
                    self.loading_label.hide()
                
                # Remove existing graphics view if present
                if hasattr(self, 'graphics_view') and self.graphics_view is not None:
                    try:
                        layout.removeWidget(self.graphics_view)
                        self.graphics_view.deleteLater()
                    except (RuntimeError, AttributeError):
                        pass
                
                # Remove existing error widget if present
                if hasattr(self, 'error_widget') and self.error_widget is not None:
                    try:
                        layout.removeWidget(self.error_widget)
                        self.error_widget.deleteLater()
                        self.error_widget = None
                    except (RuntimeError, AttributeError):
                        pass
                
                # Add new graphics view
                layout.addWidget(graphics_view)

        # Store references
        self.graphics_view = graphics_view
        self.graphics_scene = graphics_scene
        self.pixmap_item = pixmap_item
        
        # Disable Copy Error button when displaying successful images
        if hasattr(self, 'copy_error_button'):
            self.copy_error_button.setEnabled(False)
            self.copy_error_button.setStyleSheet("QPushButton:disabled { color: gray; }")
        
        # Clear any stored error text
        if hasattr(self, 'full_error_text'):
            self.full_error_text = ""
        
        # Store image data for format toggling
        self.image_data = image_data
        self.current_format = format

    def display_error(self, error_message: str, error_details: str = "", full_error: str = ""):
        """
        Display an error message in the window with full error details in a textarea.

        Args:
            error_message: Main error message to display
            error_details: Optional detailed error information for display
            full_error: Complete error response for copy/paste functionality
        """
        from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QTextEdit
        from PySide6.QtCore import Qt

        # Window will automatically stay on top due to WindowStaysOnTopHint

        # Store full error text for clipboard copy (just the raw error body)
        self.full_error_text = full_error.strip() if full_error else error_message

        # Create error display widget
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Main error message
        error_label = QLabel(f"❌ Error: {error_message}")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet("""
            QLabel {
                color: #d32f2f;
                font-size: 16px;
                font-weight: bold;
                padding: 20px;
                background-color: #ffebee;
                border: 2px solid #ffcdd2;
                border-radius: 8px;
                margin: 10px;
            }
        """)
        error_layout.addWidget(error_label)

        # Brief description if provided
        if error_details:
            details_label = QLabel(error_details)
            details_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            details_label.setStyleSheet("""
                QLabel {
                    color: #666;
                    font-size: 12px;
                    padding: 10px;
                    background-color: #f5f5f5;
                    border-radius: 4px;
                    margin: 5px 20px;
                }
            """)
            details_label.setWordWrap(True)
            error_layout.addWidget(details_label)

        # Error response body in a copyable textarea (only if we have content)
        if self.full_error_text and self.full_error_text != error_message:
            error_text_label = QLabel("Error Response:")
            error_text_label.setStyleSheet("QLabel { font-weight: bold; margin: 10px 20px 5px 20px; }")
            error_layout.addWidget(error_text_label)

            error_textarea = QTextEdit()
            error_textarea.setPlainText(self.full_error_text)
            error_textarea.setReadOnly(True)
            error_textarea.setMaximumHeight(200)
            error_textarea.setStyleSheet("""
                QTextEdit {
                    font-family: monospace;
                    font-size: 11px;
                    border: 1px solid gray;
                    border-radius: 4px;
                    margin: 5px 20px;
                    padding: 10px;
                }
            """)
            error_layout.addWidget(error_textarea)

        # NO white background for error widget - use default system background

        # Replace loading label or existing content with error widget
        central_widget = self.centralWidget()
        if central_widget:
            layout = central_widget.layout()
            if layout:
                # Remove loading label if visible
                if self.loading_label and self.loading_label.isVisible():
                    layout.removeWidget(self.loading_label)
                    self.loading_label.hide()
                
                # Remove existing graphics view if present (legacy scroll area support)
                if hasattr(self, 'graphics_view') and self.graphics_view is not None:
                    try:
                        layout.removeWidget(self.graphics_view)
                        self.graphics_view.deleteLater()
                    except (RuntimeError, AttributeError):
                        pass
                
                # Remove existing error widget if present (to prevent stacking)
                if hasattr(self, 'error_widget') and self.error_widget is not None:
                    try:
                        layout.removeWidget(self.error_widget)
                        self.error_widget.deleteLater()
                    except (RuntimeError, AttributeError):
                        pass
                
                # Add new error widget
                layout.addWidget(error_widget)

        # Store error widget reference for cleanup
        self.error_widget = error_widget
        
        # Enable Copy Error button
        if hasattr(self, 'copy_error_button'):
            self.copy_error_button.setEnabled(True)
            self.copy_error_button.setStyleSheet("QPushButton { color: black; }")
        
        # Update format label to show error state
        if self.format_label:
            self.format_label.setText("Error")
            self.format_label.show()

    def _setup_toolbar(self):
        """Setup the toolbar with action buttons."""
        from PySide6.QtWidgets import QToolBar, QPushButton, QCheckBox
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

        # Copy Error button (initially disabled)
        self.copy_error_button = QPushButton("Copy Error")
        self.copy_error_button.clicked.connect(self.copy_error_to_clipboard)
        self.copy_error_button.setEnabled(False)  # Disabled until there's an error
        self.copy_error_button.setStyleSheet("QPushButton:disabled { color: gray; }")
        toolbar.addWidget(self.copy_error_button)

        # Always on top checkbox
        self.always_on_top_checkbox = QCheckBox("Always on top")
        self.always_on_top_checkbox.setChecked(True)  # Default to on
        toolbar.addWidget(self.always_on_top_checkbox)

        # Create format label for toolbar
        from PySide6.QtWidgets import QLabel
        self.format_label = QLabel("")
        self.format_label.setStyleSheet("color: gray; font-size: 12px; padding: 5px;")
        toolbar.addWidget(self.format_label)

        # Store current format and image data
        self.current_format = "svg"  # Default to SVG
        self.image_data = None

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        from PySide6.QtGui import QShortcut, QKeySequence
        from PySide6.QtCore import Qt
        
        # Command-W (or Ctrl-W on non-Mac) to close window
        close_shortcut = QShortcut(QKeySequence.StandardKey.Close, self)
        close_shortcut.activated.connect(self.close)
        
        # Zoom shortcuts
        zoom_in_shortcut = QShortcut(QKeySequence.StandardKey.ZoomIn, self)
        zoom_in_shortcut.activated.connect(self.zoom_in)
        
        zoom_out_shortcut = QShortcut(QKeySequence.StandardKey.ZoomOut, self)
        zoom_out_shortcut.activated.connect(self.zoom_out)
        
        # Reset zoom (Cmd+0 or Ctrl+0)
        reset_zoom_shortcut = QShortcut(QKeySequence("Ctrl+0"), self)
        reset_zoom_shortcut.activated.connect(self.reset_zoom)

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
        if not hasattr(self, 'pixmap_item') or self.pixmap_item is None:
            return

        from PySide6.QtWidgets import QApplication

        # Get pixmap from the graphics item
        pixmap = self.pixmap_item.pixmap()

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

    def copy_error_to_clipboard(self):
        """Copy the full error response to clipboard."""
        if hasattr(self, 'full_error_text') and self.full_error_text:
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self.full_error_text)

    def reveal_in_finder(self):
        """Reveal the file in Finder (macOS)."""
        import subprocess
        try:
            subprocess.run(['open', '-R', self.file_path])
        except (subprocess.SubprocessError, OSError):
            # If subprocess fails, just continue
            pass

    def toggle_always_on_top(self, checked: bool):
        """Toggle the always on top window flag."""
        if checked:
            # Add the always on top flag
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            # Remove the always on top flag
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        
        # Show the window again (required when changing window flags)
        self.show()

    def zoom_in(self):
        """Zoom in on the image."""
        if hasattr(self, 'graphics_view') and self.graphics_view:
            self.graphics_view.scale(1.25, 1.25)
            self.current_zoom_scale = self.graphics_view.get_current_scale()

    def zoom_out(self):
        """Zoom out on the image."""
        if hasattr(self, 'graphics_view') and self.graphics_view:
            self.graphics_view.scale(0.8, 0.8)
            self.current_zoom_scale = self.graphics_view.get_current_scale()

    def reset_zoom(self):
        """Reset zoom to 1:1 pixel ratio (no scaling)."""
        if hasattr(self, 'graphics_view') and self.graphics_view:
            self.graphics_view.reset_zoom()
            self.current_zoom_scale = 1.0  # Reset to 1:1 pixel ratio


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
        # Window will automatically stay on top due to WindowStaysOnTopHint
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