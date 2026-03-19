from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from dacwatch.clipboard import copy_pixmap_to_clipboard, copy_text_to_clipboard


class TestCopyPixmapToClipboard:
    def test_copies_transparent_image(self, qtbot):
        """Copying without white_background preserves transparency."""
        pixmap = QPixmap(100, 100)
        pixmap.fill(Qt.GlobalColor.transparent)
        copy_pixmap_to_clipboard(pixmap, white_background=False)
        clipboard = QApplication.clipboard()
        image = clipboard.image()
        assert not image.isNull()

    def test_copies_with_white_background(self, qtbot):
        """Copying with white_background composites onto white."""
        pixmap = QPixmap(100, 100)
        pixmap.fill(Qt.GlobalColor.transparent)
        copy_pixmap_to_clipboard(pixmap, white_background=True)
        clipboard = QApplication.clipboard()
        image = clipboard.image()
        assert not image.isNull()
        # Check a corner pixel is white, not transparent
        pixel = image.pixelColor(0, 0)
        assert pixel.alpha() == 255
        assert pixel.red() == 255

    def test_respects_device_pixel_ratio(self, qtbot):
        """High-DPI pixmaps are copied correctly."""
        pixmap = QPixmap(200, 200)
        pixmap.setDevicePixelRatio(2.0)
        pixmap.fill(Qt.GlobalColor.red)
        copy_pixmap_to_clipboard(pixmap, white_background=True)
        clipboard = QApplication.clipboard()
        image = clipboard.image()
        assert not image.isNull()


class TestCopyTextToClipboard:
    def test_copies_text(self, qtbot):
        copy_text_to_clipboard("hello world")
        clipboard = QApplication.clipboard()
        assert clipboard.text() == "hello world"
