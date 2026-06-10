from PySide6.QtGui import QPixmap, QImage, QPainter
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


def copy_pixmap_to_clipboard(pixmap: QPixmap, white_background: bool = False) -> None:
    """Copy a pixmap to the system clipboard.

    If white_background is True, composites onto white first.
    Otherwise copies with transparency preserved.
    """
    if white_background:
        device_pixel_ratio = pixmap.devicePixelRatio()
        image = QImage(pixmap.width(), pixmap.height(), QImage.Format.Format_ARGB32)
        image.setDevicePixelRatio(device_pixel_ratio)
        image.fill(Qt.GlobalColor.white)
        painter = QPainter(image)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
    else:
        image = pixmap.toImage()
        if image.format() != QImage.Format.Format_ARGB32:
            image = image.convertToFormat(QImage.Format.Format_ARGB32)

    QApplication.clipboard().setImage(image)


def copy_text_to_clipboard(text: str) -> None:
    """Copy text to the system clipboard."""
    QApplication.clipboard().setText(text)


def read_text_from_clipboard() -> str:
    """Return the current text contents of the system clipboard (may be empty)."""
    return QApplication.clipboard().text()
