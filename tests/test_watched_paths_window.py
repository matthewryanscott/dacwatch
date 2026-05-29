import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dacwatch.watched_paths_window import WatchedPathsWindow


def test_refresh_populates_list(qtbot):
    """refresh() lists every watched directory and file."""
    win = WatchedPathsWindow(MagicMock())
    qtbot.addWidget(win)

    win.refresh([Path("/a/dir")], [Path("/b/file.dot")])

    assert win.list_widget.count() == 2
    texts = [win.list_widget.item(i).text() for i in range(win.list_widget.count())]
    assert any("/a/dir" in t for t in texts)
    assert any("/b/file.dot" in t for t in texts)


def test_remove_invokes_app_callback(qtbot):
    """Removing a selected file calls back into the app with path + kind."""
    app = MagicMock()
    win = WatchedPathsWindow(app)
    qtbot.addWidget(win)

    win.refresh([], [Path("/b/file.dot")])
    win.list_widget.setCurrentRow(0)
    win._remove_selected()

    app.remove_watch_path.assert_called_once_with("/b/file.dot", "file")


def test_remove_noop_without_selection(qtbot):
    """With nothing selected, Remove does nothing."""
    app = MagicMock()
    win = WatchedPathsWindow(app)
    qtbot.addWidget(win)

    win.refresh([Path("/a/dir")], [])
    win.list_widget.clearSelection()
    win._remove_selected()

    app.remove_watch_path.assert_not_called()
