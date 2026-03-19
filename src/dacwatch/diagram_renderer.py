from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt, QByteArray, QSize, QSizeF
from PySide6.QtSvg import QSvgRenderer


class DiagramRenderer:
    """Converts diagram image data (SVG/PNG bytes) to QPixmap."""

    SVG_FALLBACK_SIZE = QSize(800, 600)

    @staticmethod
    def render_to_pixmap(image_data: bytes, format: str, device_pixel_ratio: float) -> QPixmap:
        """Render image bytes to a QPixmap with high-DPI support.

        SVG: QSvgRenderer -> QPainter -> QPixmap at native resolution.
             Falls back to SVG_FALLBACK_SIZE if the SVG has no default size.
        PNG: QPixmap.loadFromData().
        Both set devicePixelRatio for Retina displays.
        """
        if format not in ("svg", "png"):
            raise ValueError(f"Unsupported format: {format!r}")

        if format == "svg":
            byte_array = QByteArray(image_data)
            svg_renderer = QSvgRenderer(byte_array)

            if not svg_renderer.isValid():
                return QPixmap()

            default_size = svg_renderer.defaultSize()
            if default_size.isEmpty() or default_size.width() <= 0 or default_size.height() <= 0:
                default_size = DiagramRenderer.SVG_FALLBACK_SIZE

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
            return pixmap
        else:
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            pixmap.setDevicePixelRatio(device_pixel_ratio)
            return pixmap

    @staticmethod
    def render_svg_to_size(
        image_data: bytes, width: int, height: int, device_pixel_ratio: float
    ) -> QPixmap:
        """Re-render SVG at exact target dimensions for auto-scale.

        Calculates the largest size that fits width x height while maintaining
        the SVG's native aspect ratio. Renders at physical pixel resolution.
        """
        byte_array = QByteArray(image_data)
        svg_renderer = QSvgRenderer(byte_array)
        if not svg_renderer.isValid():
            return QPixmap()

        svg_size = QSizeF(svg_renderer.defaultSize())
        if svg_size.isEmpty():
            return QPixmap()

        svg_size.scale(float(width), float(height), Qt.AspectRatioMode.KeepAspectRatio)

        render_width = int(svg_size.width() * device_pixel_ratio)
        render_height = int(svg_size.height() * device_pixel_ratio)

        pixmap = QPixmap(render_width, render_height)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        svg_renderer.render(painter)
        painter.end()

        pixmap.setDevicePixelRatio(device_pixel_ratio)
        return pixmap
