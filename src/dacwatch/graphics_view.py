from PySide6.QtWidgets import QGraphicsView, QLabel
from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QPainter


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
        # Disable pinch zoom when auto scale is active
        zoom = getattr(self.parent_window, 'zoom', None)
        if zoom and zoom.auto_scale_enabled:
            return True
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
                zoom = getattr(self.parent_window, 'zoom', None)
                if zoom:
                    try:
                        zoom.current_scale = self.get_current_scale()
                        label = getattr(self.parent_window, 'zoom_label', None)
                        if label:
                            zoom.update_label(label)
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
