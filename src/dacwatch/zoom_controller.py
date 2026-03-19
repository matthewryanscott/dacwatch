from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QGraphicsPixmapItem, QLabel

from .diagram_renderer import DiagramRenderer
from .graphics_view import ZoomableGraphicsView


class ZoomController:
    """Manages zoom state and auto-scale logic.

    Does not hold a reference to DiagramWindow. Methods receive
    their dependencies as arguments.
    """

    def __init__(self):
        self.current_scale: float = 1.0
        self.auto_scale_enabled: bool = False
        self._resize_timer: QTimer | None = None

    def zoom_in(self, view: ZoomableGraphicsView) -> None:
        """Zoom in by 1.25x."""
        if self.auto_scale_enabled:
            return
        try:
            view.scale(1.25, 1.25)
            self.current_scale = view.get_current_scale()
        except (RuntimeError, AttributeError):
            pass

    def zoom_out(self, view: ZoomableGraphicsView) -> None:
        """Zoom out by 0.8x."""
        if self.auto_scale_enabled:
            return
        try:
            view.scale(0.8, 0.8)
            self.current_scale = view.get_current_scale()
        except (RuntimeError, AttributeError):
            pass

    def reset(self, view: ZoomableGraphicsView) -> None:
        """Reset zoom to 1:1."""
        if self.auto_scale_enabled:
            return
        try:
            view.reset_zoom()
            self.current_scale = 1.0
        except (RuntimeError, AttributeError):
            pass

    def set_auto_scale(self, enabled: bool, view: ZoomableGraphicsView) -> None:
        """Toggle auto-scale: hide/show scrollbars."""
        self.auto_scale_enabled = enabled
        if enabled:
            view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        else:
            view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def apply_auto_scale(
        self,
        view: ZoomableGraphicsView,
        pixmap_item: QGraphicsPixmapItem,
        image_data: bytes | None,
        format: str,
        device_pixel_ratio: float,
    ) -> None:
        """Fit diagram to viewport. SVG: re-render at viewport res. PNG: fitInView."""
        if not self.auto_scale_enabled:
            return
        try:
            if format == "svg" and image_data:
                viewport_size = view.viewport().size()
                pixmap = DiagramRenderer.render_svg_to_size(
                    image_data, viewport_size.width(), viewport_size.height(),
                    device_pixel_ratio,
                )
                if not pixmap.isNull():
                    pixmap_item.setPixmap(pixmap)
                    view.resetTransform()
                    view.setSceneRect(view.scene().itemsBoundingRect())
            else:
                scene_rect = view.scene().itemsBoundingRect()
                if not scene_rect.isNull():
                    view.resetTransform()
                    view.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)
            self.current_scale = view.get_current_scale()
        except (RuntimeError, AttributeError):
            pass

    def on_resize(
        self,
        view: ZoomableGraphicsView,
        pixmap_item: QGraphicsPixmapItem,
        image_data: bytes | None,
        format: str,
        device_pixel_ratio: float,
    ) -> None:
        """Debounced resize handler. Schedules apply_auto_scale via QTimer."""
        if not self.auto_scale_enabled:
            return
        if self._resize_timer is not None:
            self._resize_timer.stop()
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(
            lambda: self.apply_auto_scale(view, pixmap_item, image_data, format, device_pixel_ratio)
        )
        self._resize_timer.start(30)

    def preserve_zoom(self, old_view: ZoomableGraphicsView) -> None:
        """Save zoom from outgoing view."""
        try:
            self.current_scale = old_view.get_current_scale()
        except (RuntimeError, AttributeError):
            pass

    def restore_zoom(self, new_view: ZoomableGraphicsView, is_first: bool) -> None:
        """Apply saved zoom (or reset to 1:1 for first display) to new view."""
        if is_first:
            new_view.resetTransform()
            self.current_scale = 1.0
        else:
            new_view.resetTransform()
            new_view.set_scale(self.current_scale)

    def update_label(self, label: QLabel) -> None:
        """Update the zoom percentage label."""
        try:
            zoom_percent = int(self.current_scale * 100)
            label.setText(f"{zoom_percent}%")
        except (RuntimeError, AttributeError):
            pass
