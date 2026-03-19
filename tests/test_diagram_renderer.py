from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap

from dacwatch.diagram_renderer import DiagramRenderer

# Minimal valid SVG for testing
MINIMAL_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="80"><rect width="100" height="80" fill="red"/></svg>'

# Minimal 1x1 red PNG (valid PNG bytes)
MINIMAL_PNG = None  # Generated in setup


def _make_png():
    """Create minimal PNG bytes from a QPixmap."""
    from PySide6.QtCore import QBuffer, QIODevice
    pixmap = QPixmap(50, 40)
    pixmap.fill(Qt.GlobalColor.red)
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    return bytes(buffer.data())


class TestRenderToPixmap:
    def test_renders_svg(self, qtbot):
        pixmap = DiagramRenderer.render_to_pixmap(MINIMAL_SVG, "svg", 1.0)
        assert not pixmap.isNull()
        assert pixmap.width() == 100
        assert pixmap.height() == 80

    def test_renders_svg_with_hidpi(self, qtbot):
        pixmap = DiagramRenderer.render_to_pixmap(MINIMAL_SVG, "svg", 2.0)
        assert not pixmap.isNull()
        # Physical pixels are 2x, but devicePixelRatio is set
        assert pixmap.width() == 200
        assert pixmap.height() == 160
        assert pixmap.devicePixelRatio() == 2.0

    def test_renders_png(self, qtbot):
        png_data = _make_png()
        pixmap = DiagramRenderer.render_to_pixmap(png_data, "png", 1.0)
        assert not pixmap.isNull()
        assert pixmap.width() == 50

    def test_invalid_svg_returns_null_pixmap(self, qtbot):
        pixmap = DiagramRenderer.render_to_pixmap(b"not valid svg", "svg", 1.0)
        assert pixmap.isNull()

    def test_rejects_unsupported_format(self, qtbot):
        import pytest
        with pytest.raises(ValueError):
            DiagramRenderer.render_to_pixmap(b"data", "gif", 1.0)


class TestRenderSvgToSize:
    def test_renders_to_target_size(self, qtbot):
        pixmap = DiagramRenderer.render_svg_to_size(MINIMAL_SVG, 200, 200, 1.0)
        assert not pixmap.isNull()
        # Should fit within 200x200 maintaining aspect ratio (100:80 = 5:4)
        # Width-limited: 200x160
        assert pixmap.width() == 200
        assert pixmap.height() == 160

    def test_renders_with_hidpi(self, qtbot):
        pixmap = DiagramRenderer.render_svg_to_size(MINIMAL_SVG, 200, 200, 2.0)
        assert not pixmap.isNull()
        assert pixmap.width() == 400  # 200 * 2.0
        assert pixmap.devicePixelRatio() == 2.0

    def test_invalid_svg_returns_null_pixmap(self, qtbot):
        pixmap = DiagramRenderer.render_svg_to_size(b"invalid", 200, 200, 1.0)
        assert pixmap.isNull()
