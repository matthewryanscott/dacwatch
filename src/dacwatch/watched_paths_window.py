"""The Watched Paths window: lists watched directories and files, and lets the
user remove a watch or reveal a path in the system file manager.

Opened from the "Window" menu. Closing it merely hides the window (the app keeps
running with no visible windows), so reopening from the menu reuses the same
instance.
"""

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Roles for stashing path metadata on list items.
_PATH_ROLE = Qt.ItemDataRole.UserRole
_KIND_ROLE = Qt.ItemDataRole.UserRole + 1


def reveal_path(path: str):
    """Reveal a path in Finder (macOS) / file manager (Linux/Windows)."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", path])
        elif sys.platform.startswith("linux"):
            target = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
            subprocess.run(["xdg-open", target])
        elif sys.platform == "win32":
            subprocess.run(["explorer", "/select,", path])
    except (subprocess.SubprocessError, OSError):
        pass


class WatchedPathsWindow(QMainWindow):
    """Shows the set of watched directories and files."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self.setWindowTitle("DaCWatch - Watched Paths")
        self.setGeometry(150, 150, 520, 360)
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._update_buttons)
        self.list_widget.itemDoubleClicked.connect(lambda _: self._reveal_selected())
        layout.addWidget(self.list_widget)

        buttons = QHBoxLayout()
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._remove_selected)
        buttons.addWidget(self.remove_button)

        self.reveal_button = QPushButton("Reveal")
        self.reveal_button.clicked.connect(self._reveal_selected)
        buttons.addWidget(self.reveal_button)

        buttons.addStretch()
        layout.addLayout(buttons)

        self._update_buttons()

    def refresh(self, directories: list[Path], files: list[Path]):
        """Repopulate the list from the current watched dirs and files."""
        self.list_widget.clear()
        for directory in sorted(directories, key=str):
            self._add_item(directory, "directory")
        for file in sorted(files, key=str):
            self._add_item(file, "file")
        self._update_buttons()

    def _add_item(self, path: Path, kind: str):
        item = QListWidgetItem(f"[{'dir' if kind == 'directory' else 'file'}]  {path}")
        item.setData(_PATH_ROLE, str(path))
        item.setData(_KIND_ROLE, kind)
        self.list_widget.addItem(item)

    def _selected_item(self) -> QListWidgetItem | None:
        items = self.list_widget.selectedItems()
        return items[0] if items else None

    def _update_buttons(self):
        has_selection = self._selected_item() is not None
        self.remove_button.setEnabled(has_selection)
        self.reveal_button.setEnabled(has_selection)

    def _remove_selected(self):
        item = self._selected_item()
        if item is None:
            return
        self._app.remove_watch_path(item.data(_PATH_ROLE), item.data(_KIND_ROLE))

    def _reveal_selected(self):
        item = self._selected_item()
        if item is None:
            return
        reveal_path(item.data(_PATH_ROLE))
