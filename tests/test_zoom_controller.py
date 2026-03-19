from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from dacwatch.zoom_controller import ZoomController
from dacwatch.graphics_view import ZoomableGraphicsView


class TestZoomInOut:
    def test_zoom_in_scales_view(self, qtbot):
        view = ZoomableGraphicsView()
        qtbot.addWidget(view)
        scene = QGraphicsScene()
        scene.addItem(QGraphicsPixmapItem(QPixmap(100, 100)))
        view.setScene(scene)

        ctrl = ZoomController()
        ctrl.zoom_in(view)
        assert ctrl.current_scale > 1.0

    def test_zoom_out_scales_view(self, qtbot):
        view = ZoomableGraphicsView()
        qtbot.addWidget(view)
        scene = QGraphicsScene()
        scene.addItem(QGraphicsPixmapItem(QPixmap(100, 100)))
        view.setScene(scene)

        ctrl = ZoomController()
        ctrl.zoom_out(view)
        assert ctrl.current_scale < 1.0

    def test_zoom_blocked_when_auto_scale_enabled(self, qtbot):
        view = ZoomableGraphicsView()
        qtbot.addWidget(view)
        scene = QGraphicsScene()
        scene.addItem(QGraphicsPixmapItem(QPixmap(100, 100)))
        view.setScene(scene)

        ctrl = ZoomController()
        ctrl.auto_scale_enabled = True
        ctrl.zoom_in(view)
        assert ctrl.current_scale == 1.0  # unchanged

    def test_reset_zoom(self, qtbot):
        view = ZoomableGraphicsView()
        qtbot.addWidget(view)
        scene = QGraphicsScene()
        scene.addItem(QGraphicsPixmapItem(QPixmap(100, 100)))
        view.setScene(scene)

        ctrl = ZoomController()
        ctrl.zoom_in(view)
        assert ctrl.current_scale > 1.0
        ctrl.reset(view)
        assert ctrl.current_scale == 1.0


class TestUpdateLabel:
    def test_updates_label_text(self, qtbot):
        label = QLabel()
        qtbot.addWidget(label)

        ctrl = ZoomController()
        ctrl.current_scale = 1.5
        ctrl.update_label(label)
        assert label.text() == "150%"

    def test_updates_at_100_percent(self, qtbot):
        label = QLabel()
        qtbot.addWidget(label)

        ctrl = ZoomController()
        ctrl.update_label(label)
        assert label.text() == "100%"


class TestPreserveRestoreZoom:
    def test_preserve_and_restore(self, qtbot):
        view1 = ZoomableGraphicsView()
        qtbot.addWidget(view1)
        scene1 = QGraphicsScene()
        scene1.addItem(QGraphicsPixmapItem(QPixmap(100, 100)))
        view1.setScene(scene1)

        ctrl = ZoomController()
        ctrl.zoom_in(view1)
        saved_scale = ctrl.current_scale

        view2 = ZoomableGraphicsView()
        qtbot.addWidget(view2)
        scene2 = QGraphicsScene()
        scene2.addItem(QGraphicsPixmapItem(QPixmap(100, 100)))
        view2.setScene(scene2)

        ctrl.preserve_zoom(view1)
        ctrl.restore_zoom(view2, is_first=False)
        assert abs(view2.transform().m11() - saved_scale) < 0.01

    def test_restore_first_display_resets(self, qtbot):
        view = ZoomableGraphicsView()
        qtbot.addWidget(view)
        scene = QGraphicsScene()
        scene.addItem(QGraphicsPixmapItem(QPixmap(100, 100)))
        view.setScene(scene)

        ctrl = ZoomController()
        ctrl.current_scale = 2.0
        ctrl.restore_zoom(view, is_first=True)
        assert ctrl.current_scale == 1.0


class TestAutoScale:
    def test_set_auto_scale_on_hides_scrollbars(self, qtbot):
        view = ZoomableGraphicsView()
        qtbot.addWidget(view)

        ctrl = ZoomController()
        ctrl.set_auto_scale(True, view)
        assert ctrl.auto_scale_enabled is True
        assert view.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    def test_set_auto_scale_off_restores_scrollbars(self, qtbot):
        view = ZoomableGraphicsView()
        qtbot.addWidget(view)

        ctrl = ZoomController()
        ctrl.set_auto_scale(True, view)
        ctrl.set_auto_scale(False, view)
        assert ctrl.auto_scale_enabled is False
        assert view.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
