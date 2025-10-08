from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import json
import os

# PySide imports
from PySide6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtCore import Qt, QEvent, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QAction


class ToastWidget(QLabel):
    """A toast notification widget that appears briefly over the main window."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()
    
    def show_toast(self, message: str, duration_ms: int = 500):
        """Show the toast with a message for the specified duration."""
        self.setText(message)
        self.adjustSize()
        
        # Position in center of parent widget
        from PySide6.QtWidgets import QWidget
        parent_widget = self.parent()
        if isinstance(parent_widget, QWidget):
            parent_rect = parent_widget.rect()
            x = parent_rect.center().x() - self.width() // 2
            y = parent_rect.center().y() - self.height() // 2
            self.move(x, y)
            self.setGeometry(x, y, self.width(), self.height())
        
        self.show()
        self.raise_()
        self.repaint()  # Force immediate update
        
        # Auto-hide after duration
        QTimer.singleShot(duration_ms, self.hide)


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
        
        # Enable keyboard focus so arrow keys can be used for navigation
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Enable gesture support for pinch-to-zoom
        self.grabGesture(Qt.GestureType.PinchGesture)
        
        # Zoom limits
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.zoom_factor_base = 1.0015
        
        # Window dragging state
        self.dragging_window = False
        self.drag_start_position = None

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
                    try:
                        self.parent_window.current_zoom_scale = self.get_current_scale()
                        # Update zoom label if available
                        if hasattr(self.parent_window, '_update_zoom_label'):
                            self.parent_window._update_zoom_label()
                    except (RuntimeError, AttributeError):
                        # Parent window might have been deleted
                        pass
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

    def mousePressEvent(self, event):
        """Handle mouse press events for window dragging and normal graphics view behavior."""
        from PySide6.QtCore import Qt
        
        if event.button() == Qt.MouseButton.LeftButton:
            # Start window drag for any left click in the graphics view
            # This allows dragging from anywhere in the image viewer area
            self.dragging_window = True
            self.drag_start_position = event.globalPosition().toPoint()
            event.accept()
            return
        
        # Let the base class handle other cases (right click, etc.)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events for window dragging and normal graphics view behavior."""
        if self.dragging_window and self.drag_start_position is not None and self.parent_window:
            try:
                # Calculate the movement delta
                delta = event.globalPosition().toPoint() - self.drag_start_position
                
                # Move the parent window
                new_position = self.parent_window.pos() + delta
                self.parent_window.move(new_position)
                
                # Update drag start position for next move event
                self.drag_start_position = event.globalPosition().toPoint()
                event.accept()
                return
            except (RuntimeError, AttributeError):
                # Parent window might have been deleted
                self.dragging_window = False
                self.drag_start_position = None
        
        # Let the base class handle other cases
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events for window dragging and normal graphics view behavior."""
        from PySide6.QtCore import Qt
        
        if event.button() == Qt.MouseButton.LeftButton and self.dragging_window:
            # Stop window dragging
            self.dragging_window = False
            self.drag_start_position = None
            event.accept()
            return
        
        # Let the base class handle other cases
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Handle double-click events to trigger fit action."""
        from PySide6.QtCore import Qt
        
        if event.button() == Qt.MouseButton.LeftButton:
            # Trigger fit action on parent window if available
            if self.parent_window and hasattr(self.parent_window, 'fit_to_diagram'):
                try:
                    self.parent_window.fit_to_diagram()
                    event.accept()
                    return
                except (RuntimeError, AttributeError):
                    # Parent window might have been deleted
                    pass
        
        # Let the base class handle other cases
        super().mouseDoubleClickEvent(event)


class DiagramWindow(QMainWindow):
    """A window for displaying diagram files."""

    def __init__(self, file_path: str, window_manager: Optional['WindowManager'] = None):
        super().__init__()
        self.file_path = file_path
        self.window_manager = window_manager
        self.loading_label: Optional[QLabel] = None
        self.format_label: Optional[QLabel] = None
        self.format_toggle_callback: Optional[Callable[[str], None]] = None
        self.current_zoom_scale: float = 1.0  # Store current zoom level
        self.is_first_display: bool = True  # Track if this is the first image display
        self.should_auto_fit: bool = True  # Track if window should auto-fit on next image display
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        # Set window title
        file_name = Path(self.file_path).name
        self.setWindowTitle(f"DaCWatch - {file_name}")

        # Window stays on top controlled by action (macOS only - Linux has window visibility issues)
        # Initial state set to False in _setup_actions()

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

        # Setup actions first (needed by toolbar)
        self._setup_actions()
        
        # Setup toolbar
        self._setup_toolbar()
        
        # Setup keyboard shortcuts
        self._setup_shortcuts()
        
        # Setup toast notification
        self.toast = ToastWidget(self)

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
            try:
                self.current_zoom_scale = self.graphics_view.get_current_scale()
            except (RuntimeError, AttributeError):
                # Graphics view might have been deleted, use current stored value
                pass
        
        if self.is_first_display:
            # First time - reset transform for true 1:1 display (no scaling)
            graphics_view.resetTransform()
            self.current_zoom_scale = 1.0
            self.is_first_display = False
        else:
            # Subsequent updates - reset transform first, then apply saved scale
            graphics_view.resetTransform()
            graphics_view.set_scale(self.current_zoom_scale)
        
        # Auto-fit window to diagram if this is the first display or after reappearing
        if self.should_auto_fit and self.isVisible():
            self.should_auto_fit = False
            from PySide6.QtCore import QTimer
            def auto_fit_after_display():
                try:
                    self.fit_to_diagram()
                except (RuntimeError, AttributeError):
                    pass
            # Use a small delay to ensure the graphics view is fully set up
            QTimer.singleShot(50, auto_fit_after_display)
        
        # Update zoom label
        self._update_zoom_label()

        # Update format radio buttons
        if hasattr(self, 'svg_radio') and hasattr(self, 'png_radio'):
            # Re-enable radio buttons (in case they were disabled due to error)
            self.svg_radio.setEnabled(True)
            self.png_radio.setEnabled(True)
            
            if format == "svg":
                self.svg_radio.setChecked(True)
            else:
                self.png_radio.setChecked(True)

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
                        self.graphics_view = None  # Clear reference immediately
                    except (RuntimeError, AttributeError):
                        pass
                
                # Remove existing error widget if present
                if hasattr(self, 'error_widget') and self.error_widget is not None:
                    try:
                        layout.removeWidget(self.error_widget)
                        self.error_widget.deleteLater()
                        self.error_widget = None  # Clear reference immediately
                    except (RuntimeError, AttributeError):
                        pass
                
                # Add new graphics view
                layout.addWidget(graphics_view)

        # Store references
        self.graphics_view = graphics_view
        self.graphics_scene = graphics_scene
        self.pixmap_item = pixmap_item
        
        # Set focus to the graphics view for keyboard navigation
        # Use a small delay to ensure focus is set after all other UI updates complete
        from PySide6.QtCore import QTimer
        graphics_view.setFocus()
        
        # Set tab order to ensure graphics view is first in tab order
        if hasattr(self, 'svg_radio') and self.svg_radio:
            self.setTabOrder(graphics_view, self.svg_radio)
        
        # Use a delayed focus set to override any competing focus attempts
        def safe_set_focus():
            try:
                if hasattr(self, 'graphics_view') and self.graphics_view:
                    self.graphics_view.setFocus()
            except (RuntimeError, AttributeError):
                pass  # Widget may have been deleted
        QTimer.singleShot(50, safe_set_focus)
        
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
        
        # In error state, disable format radio buttons
        if hasattr(self, 'svg_radio') and hasattr(self, 'png_radio'):
            self.svg_radio.setEnabled(False)
            self.png_radio.setEnabled(False)

    def _setup_toolbar(self):
        """Setup the toolbar with action buttons."""
        from PySide6.QtWidgets import QToolBar, QPushButton, QCheckBox
        from PySide6.QtCore import Qt

        # Create toolbar
        toolbar = QToolBar("Diagram Actions")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        # Copy image button
        self.copy_image_button = QPushButton("📋 Image")
        self.copy_image_button.clicked.connect(self.copy_image_to_clipboard)
        toolbar.addWidget(self.copy_image_button)

        # Copy source button
        self.copy_source_button = QPushButton("📋 Source")
        self.copy_source_button.clicked.connect(self.copy_source_to_clipboard)
        toolbar.addWidget(self.copy_source_button)

        # Copy Error button (initially disabled)
        self.copy_error_button = QPushButton("📋 Error")
        self.copy_error_button.clicked.connect(self.copy_error_to_clipboard)
        self.copy_error_button.setEnabled(False)  # Disabled until there's an error
        self.copy_error_button.setStyleSheet("QPushButton:disabled { color: gray; }")
        toolbar.addWidget(self.copy_error_button)

        # Fit button to size window to diagram
        self.fit_button = QPushButton("Fit")
        self.fit_button.clicked.connect(self.fit_to_diagram)
        toolbar.addWidget(self.fit_button)

        # Reveal in Finder button
        self.reveal_button = QPushButton("Reveal")
        self.reveal_button.clicked.connect(self.reveal_in_finder)
        toolbar.addWidget(self.reveal_button)

        # Always on top toggle - macOS only (Linux has issues with window disappearing)
        import sys
        if sys.platform == 'darwin':
            toolbar.addAction(self.always_on_top_action)

        # Create format selection radio buttons
        from PySide6.QtWidgets import QLabel, QRadioButton, QHBoxLayout, QWidget, QButtonGroup
        
        # Create a widget to hold the radio buttons
        format_widget = QWidget()
        format_layout = QHBoxLayout(format_widget)
        format_layout.setContentsMargins(5, 0, 5, 0)
        format_layout.setSpacing(5)
        
        # Create radio buttons for format selection
        self.svg_radio = QRadioButton("SVG")
        self.png_radio = QRadioButton("PNG")
        
        # Style the radio buttons
        radio_style = """
            QRadioButton {
                font-size: 12px;
                padding: 2px;
            }
        """
        self.svg_radio.setStyleSheet(radio_style)
        self.png_radio.setStyleSheet(radio_style)
        
        # Create button group to manage exclusive selection
        self.format_button_group = QButtonGroup()
        self.format_button_group.addButton(self.svg_radio, 0)  # 0 for SVG
        self.format_button_group.addButton(self.png_radio, 1)  # 1 for PNG
        
        # Set default selection (SVG)
        self.svg_radio.setChecked(True)
        
        # Connect signal for format changes
        self.format_button_group.idToggled.connect(self._on_format_radio_toggled)
        
        # Add radio buttons to layout
        format_layout.addWidget(self.svg_radio)
        format_layout.addWidget(self.png_radio)
        
        # Add format widget to toolbar
        toolbar.addWidget(format_widget)
        
        # Create zoom level label for toolbar
        self.zoom_label = QLabel("100%")
        self.zoom_label.setStyleSheet("color: gray; font-size: 12px; padding: 5px;")
        toolbar.addWidget(self.zoom_label)

        # Store current format and image data
        self.current_format = "svg"  # Default to SVG
        self.image_data = None
        
        # Update initial zoom label
        self._update_zoom_label()
        
        # Update initial zoom label
        self._update_zoom_label()

    def _update_zoom_label(self):
        """Update the zoom label with current zoom percentage."""
        if hasattr(self, 'zoom_label') and self.zoom_label:
            try:
                # Convert zoom scale to percentage
                zoom_percent = int(self.current_zoom_scale * 100)
                self.zoom_label.setText(f"{zoom_percent}%")
            except (RuntimeError, AttributeError):
                # Label might have been deleted
                pass

    def _on_format_radio_toggled(self, button_id, checked):
        """Handle format radio button toggle."""
        if checked:  # Only act when a button is checked (not unchecked)
            new_format = "svg" if button_id == 0 else "png"
            
            # Only trigger re-render if format actually changed
            if new_format != self.current_format:
                # We need to re-render with the new format
                if hasattr(self, 'format_toggle_callback') and self.format_toggle_callback:
                    self.format_toggle_callback(new_format)

    def _setup_actions(self):
        """Setup actions for toolbar and shortcuts."""
        # Always on top action - checkable for clean state management
        self.always_on_top_action = QAction("Always on top", self)
        self.always_on_top_action.setCheckable(True)
        self.always_on_top_action.setChecked(False)  # Default to off
        self.always_on_top_action.triggered.connect(self._handle_always_on_top)

    def _handle_always_on_top(self, checked: bool):
        """Handle always on top toggle with clean state management."""
        if checked:
            # Add the always on top flag
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            # Remove the always on top flag
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        
        # Show the window again (required when changing window flags)
        self.show()
        
        # Set focus to graphics view if it exists
        # Use a small delay to ensure focus is set after all other UI updates
        if hasattr(self, 'graphics_view') and self.graphics_view:
            from PySide6.QtCore import QTimer
            def safe_set_focus():
                try:
                    if hasattr(self, 'graphics_view') and self.graphics_view:
                        self.graphics_view.setFocus()
                except (RuntimeError, AttributeError):
                    pass
            QTimer.singleShot(50, safe_set_focus)

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
        
        # Additional zoom in shortcut for Cmd+= (without shift)
        zoom_in_equal_shortcut = QShortcut(QKeySequence("Ctrl+="), self)
        zoom_in_equal_shortcut.activated.connect(self.zoom_in)
        
        zoom_out_shortcut = QShortcut(QKeySequence.StandardKey.ZoomOut, self)
        zoom_out_shortcut.activated.connect(self.zoom_out)
        
        # Reset zoom (Cmd+0 or Ctrl+0)
        reset_zoom_shortcut = QShortcut(QKeySequence("Ctrl+0"), self)
        reset_zoom_shortcut.activated.connect(self.reset_zoom)
        
        # Copy image (Cmd+C)
        copy_image_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self)
        copy_image_shortcut.activated.connect(self.copy_image_to_clipboard)

        # Copy image with white background (Cmd+Option+C)
        copy_white_bg_shortcut = QShortcut(QKeySequence("Ctrl+Alt+C"), self)
        copy_white_bg_shortcut.activated.connect(self.copy_image_with_white_background)

        # Copy source (Cmd+Shift+C)
        copy_source_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        copy_source_shortcut.activated.connect(self.copy_source_to_clipboard)
        
        # Toggle format (Cmd+F)
        toggle_format_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        toggle_format_shortcut.activated.connect(self.toggle_format)

        # Toggle always on top (Cmd+T on Mac only - disabled on Linux due to window visibility issues)
        import sys
        if sys.platform == 'darwin':
            toggle_always_on_top_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
            toggle_always_on_top_shortcut.activated.connect(lambda: self.always_on_top_action.trigger())
        
        # Reveal in Finder (Cmd+R on Mac, Ctrl+R on others)
        reveal_finder_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        reveal_finder_shortcut.activated.connect(self.reveal_in_finder)
        
        # Fit to diagram (F key)
        fit_shortcut = QShortcut(QKeySequence("F"), self)
        fit_shortcut.activated.connect(self.fit_to_diagram)

        # Note: Window cycling shortcuts (Cmd+] and Cmd+[) are registered at the
        # application level in app.py to ensure they work across all windows

    def toggle_format(self):
        """Toggle between SVG and PNG formats using radio buttons."""
        if not hasattr(self, 'image_data') or self.image_data is None:
            return

        # Toggle the radio button selection
        if hasattr(self, 'svg_radio') and hasattr(self, 'png_radio'):
            if self.svg_radio.isChecked():
                self.png_radio.setChecked(True)  # This will trigger the format change
            else:
                self.svg_radio.setChecked(True)  # This will trigger the format change

    def copy_image_to_clipboard(self):
        """Copy the current image to clipboard."""
        if not hasattr(self, 'pixmap_item') or self.pixmap_item is None:
            return

        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtGui import QImage
            from PySide6.QtCore import QBuffer, QIODevice

            # Get pixmap from the graphics item
            pixmap = self.pixmap_item.pixmap()

            # Convert to QImage with explicit transparency support
            image = pixmap.toImage()

            # Ensure the image has an alpha channel for transparency
            if image.format() != QImage.Format.Format_ARGB32:
                image = image.convertToFormat(QImage.Format.Format_ARGB32)

            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setImage(image)

            # Show toast notification
            if hasattr(self, 'toast') and self.toast:
                self.toast.show_toast("Copied image")
        except (RuntimeError, AttributeError):
            # Pixmap item or toast might have been deleted
            pass

    def copy_image_with_white_background(self):
        """Copy the current image to clipboard with white background instead of transparent."""
        if not hasattr(self, 'pixmap_item') or self.pixmap_item is None:
            return

        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtGui import QImage, QPainter
            from PySide6.QtCore import Qt

            # Get pixmap from the graphics item
            pixmap = self.pixmap_item.pixmap()

            # Get device pixel ratio to handle high-DPI displays correctly
            device_pixel_ratio = pixmap.devicePixelRatio()

            # Get actual pixel dimensions (physical size)
            width = pixmap.width()
            height = pixmap.height()

            # Create a new image with white background at the same physical size
            image = QImage(width, height, QImage.Format.Format_ARGB32)
            image.setDevicePixelRatio(device_pixel_ratio)
            image.fill(Qt.GlobalColor.white)

            # Draw the original pixmap on top of the white background
            painter = QPainter(image)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()

            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setImage(image)

            # Show toast notification
            if hasattr(self, 'toast') and self.toast:
                self.toast.show_toast("Copied with white background")
        except (RuntimeError, AttributeError):
            # Pixmap item or toast might have been deleted
            pass

    def copy_source_to_clipboard(self):
        """Copy the source code to clipboard."""
        try:
            with open(self.file_path, 'r') as f:
                source_code = f.read()

            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(source_code)
            
            # Show toast notification
            self.toast.show_toast("Copied source")
        except Exception:
            # Silently ignore file read errors
            pass

    def copy_error_to_clipboard(self):
        """Copy the full error response to clipboard."""
        if hasattr(self, 'full_error_text') and self.full_error_text:
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self.full_error_text)

    def reveal_in_finder(self):
        """Reveal the file in Finder (macOS) or file manager (Linux/Windows)."""
        import subprocess
        import sys
        import os
        try:
            if sys.platform == 'darwin':
                # macOS: open -R reveals in Finder
                subprocess.run(['open', '-R', self.file_path])
            elif sys.platform.startswith('linux'):
                # Linux: xdg-open the parent directory
                parent_dir = os.path.dirname(os.path.abspath(self.file_path))
                subprocess.run(['xdg-open', parent_dir])
            elif sys.platform == 'win32':
                # Windows: explorer /select reveals in Explorer
                subprocess.run(['explorer', '/select,', self.file_path])
        except (subprocess.SubprocessError, OSError):
            # If subprocess fails, just continue
            pass



    def zoom_in(self):
        """Zoom in on the image."""
        if hasattr(self, 'graphics_view') and self.graphics_view:
            try:
                self.graphics_view.scale(1.25, 1.25)
                self.current_zoom_scale = self.graphics_view.get_current_scale()
                self._update_zoom_label()
            except (RuntimeError, AttributeError):
                # Graphics view might have been deleted
                pass

    def zoom_out(self):
        """Zoom out on the image."""
        if hasattr(self, 'graphics_view') and self.graphics_view:
            try:
                self.graphics_view.scale(0.8, 0.8)
                self.current_zoom_scale = self.graphics_view.get_current_scale()
                self._update_zoom_label()
            except (RuntimeError, AttributeError):
                # Graphics view might have been deleted
                pass

    def reset_zoom(self):
        """Reset zoom to 1:1 pixel ratio (no scaling)."""
        if hasattr(self, 'graphics_view') and self.graphics_view:
            try:
                self.graphics_view.reset_zoom()
                self.current_zoom_scale = 1.0  # Reset to 1:1 pixel ratio
                self._update_zoom_label()
            except (RuntimeError, AttributeError):
                # Graphics view might have been deleted
                pass

    def fit_to_diagram(self):
        """Resize the window to fit the diagram exactly with no scrollbars."""
        if not hasattr(self, 'pixmap_item') or self.pixmap_item is None:
            return
        
        # Check if graphics view exists and is not deleted    
        if not hasattr(self, 'graphics_view') or self.graphics_view is None:
            return
            
        try:
            # Get the pixmap dimensions (these are the logical dimensions, not physical)
            pixmap = self.pixmap_item.pixmap()
            pixmap_size = pixmap.size()
            
            # Account for device pixel ratio to get actual display size
            device_pixel_ratio = self.devicePixelRatio()
            logical_width = int(pixmap_size.width() / device_pixel_ratio)
            logical_height = int(pixmap_size.height() / device_pixel_ratio)
            
            # Reset zoom to 1:1 first to get accurate measurements
            self.reset_zoom()
            
            # Get the graphics view's viewport size to understand available space
            viewport_size = self.graphics_view.viewport().size()
            
            # Calculate how much space is taken up by non-viewport elements
            view_total_size = self.graphics_view.size()
            scrollbar_width = view_total_size.width() - viewport_size.width()
            scrollbar_height = view_total_size.height() - viewport_size.height()
            
            # Calculate the required graphics view size (diagram + scrollbar space)
            required_view_width = logical_width + scrollbar_width
            required_view_height = logical_height + scrollbar_height
            
            # Calculate the current "chrome" size (window - graphics view)
            current_window_size = self.size()
            current_view_size = self.graphics_view.size()
            chrome_width = current_window_size.width() - current_view_size.width()
            chrome_height = current_window_size.height() - current_view_size.height()
            
            # Calculate the target window size
            target_width = required_view_width + chrome_width
            target_height = required_view_height + chrome_height
            
            # Add a small buffer to ensure no scrollbars appear
            buffer_width = 4
            buffer_height = 4
            
            # Resize the window to exactly fit the diagram
            self.resize(target_width + buffer_width, target_height + buffer_height)
        except (RuntimeError, AttributeError):
            # Graphics view or pixmap might have been deleted
            pass

    def showEvent(self, event):
        """Handle window show event to set focus to graphics view."""
        super().showEvent(event)
        
        # Set focus to graphics view for keyboard navigation
        # Use a small delay to ensure focus is set after all other UI updates
        if hasattr(self, 'graphics_view') and self.graphics_view:
            from PySide6.QtCore import QTimer
            def safe_set_focus():
                try:
                    if hasattr(self, 'graphics_view') and self.graphics_view:
                        self.graphics_view.setFocus()
                except (RuntimeError, AttributeError):
                    pass
            QTimer.singleShot(50, safe_set_focus)
    
    def hideEvent(self, event):
        """Handle window hide event to prepare for auto-fit on reappear."""
        super().hideEvent(event)
        # Set flag so that auto-fit will trigger when window reappears and image is displayed
        self.should_auto_fit = True

    def focusInEvent(self, event):
        """Handle window focus event to set focus to graphics view."""
        super().focusInEvent(event)
        # Set focus to graphics view for keyboard navigation
        # Use a small delay to ensure focus is set after all other UI updates
        if hasattr(self, 'graphics_view') and self.graphics_view:
            from PySide6.QtCore import QTimer
            def safe_set_focus():
                try:
                    if hasattr(self, 'graphics_view') and self.graphics_view:
                        self.graphics_view.setFocus()
                except (RuntimeError, AttributeError):
                    pass
            QTimer.singleShot(50, safe_set_focus)

    def closeEvent(self, event):
        """Handle window close event to clean up from window manager."""
        super().closeEvent(event)
        # Notify window manager to remove this window from its tracking
        if self.window_manager:
            self.window_manager.remove_window_by_path(self.file_path)


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

    def remove_window_by_path(self, file_path: str):
        """
        Remove a window from tracking (called when window is closed manually).

        Args:
            file_path: Path to the file
        """
        if file_path in self.windows:
            # Save window state before removing
            self.save_window_state(file_path)
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

    def cycle_to_next_window(self, backward=False):
        """Cycle to the next/previous window in the list of open windows."""
        if len(self.windows) <= 1:
            return  # Nothing to cycle if 0 or 1 windows

        from PySide6.QtWidgets import QApplication

        # Get currently active window
        active_window = QApplication.activeWindow()

        # Get list of windows in a consistent order
        window_list = list(self.windows.values())

        # Find current window index
        try:
            current_index = window_list.index(active_window)
            if backward:
                next_index = (current_index - 1) % len(window_list)
            else:
                next_index = (current_index + 1) % len(window_list)
        except (ValueError, AttributeError):
            # Active window not in our list or no active window, just use first
            next_index = 0

        # Activate next window
        next_window = window_list[next_index]
        if next_window:
            try:
                next_window.raise_()
                next_window.activateWindow()
            except (RuntimeError, AttributeError):
                # Window might have been deleted
                pass

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
        return DiagramWindow(file_path, window_manager=self)