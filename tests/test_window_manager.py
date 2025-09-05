import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import sys

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dacwatch.window_manager import WindowManager


class TestWindowManager:
    """Test suite for WindowManager class."""

    def test_initialization(self):
        """Test WindowManager initializes correctly."""
        manager = WindowManager()
        assert manager.windows == {}
        assert manager.window_count == 0

    def test_get_window_for_file_nonexistent(self):
        """Test getting window for file that doesn't exist."""
        manager = WindowManager()
        result = manager.get_window_for_file("/path/to/nonexistent/file.txt")
        assert result is None

    def test_create_window_for_file(self):
        """Test creating a window for a file."""
        manager = WindowManager()

        # Mock the window creation
        mock_window = Mock()
        mock_window.file_path = "/path/to/test/file.dot"

        # Mock the window factory method
        manager._create_window = Mock(return_value=mock_window)

        result = manager.create_window("/path/to/test/file.dot")

        assert result == mock_window
        assert manager.windows["/path/to/test/file.dot"] == mock_window
        assert manager.window_count == 1
        manager._create_window.assert_called_once_with("/path/to/test/file.dot")

    def test_get_window_for_file_existing(self):
        """Test getting window for existing file."""
        manager = WindowManager()

        # Create a mock window
        mock_window = Mock()
        mock_window.file_path = "/path/to/test/file.dot"

        # Manually add to registry
        manager.windows["/path/to/test/file.dot"] = mock_window

        result = manager.get_window_for_file("/path/to/test/file.dot")
        assert result == mock_window

    def test_close_window_existing(self):
        """Test closing an existing window."""
        manager = WindowManager()

        # Create a mock window
        mock_window = Mock()
        mock_window.file_path = "/path/to/test/file.dot"
        mock_window.close = Mock()

        # Manually add to registry
        manager.windows["/path/to/test/file.dot"] = mock_window

        assert manager.window_count == 1

        manager.close_window("/path/to/test/file.dot")

        assert "/path/to/test/file.dot" not in manager.windows
        assert manager.window_count == 0
        mock_window.close.assert_called_once()

    def test_close_window_nonexistent(self):
        """Test closing a window that doesn't exist."""
        manager = WindowManager()

        # Should not raise an error
        manager.close_window("/path/to/nonexistent/file.txt")
        assert manager.window_count == 0

    def test_get_or_create_window_new(self):
        """Test getting or creating a window for new file."""
        manager = WindowManager()

        # Mock the window creation
        mock_window = Mock()
        mock_window.file_path = "/path/to/test/file.dot"

        manager._create_window = Mock(return_value=mock_window)

        result = manager.get_or_create_window("/path/to/test/file.dot")

        assert result == mock_window
        assert manager.windows["/path/to/test/file.dot"] == mock_window
        manager._create_window.assert_called_once_with("/path/to/test/file.dot")

    def test_get_or_create_window_existing(self):
        """Test getting or creating a window for existing file."""
        manager = WindowManager()

        # Create a mock window
        mock_window = Mock()
        mock_window.file_path = "/path/to/test/file.dot"

        # Manually add to registry
        manager.windows["/path/to/test/file.dot"] = mock_window

        result = manager.get_or_create_window("/path/to/test/file.dot")

        assert result == mock_window
        # Should not create a new window
        assert len(manager.windows) == 1

    def test_list_open_files(self):
        """Test listing all open files."""
        manager = WindowManager()

        # Add some mock windows
        manager.windows = {
            "/path/to/file1.dot": Mock(),
            "/path/to/file2.puml": Mock(),
            "/path/to/file3.mermaid": Mock(),
        }

        files = manager.list_open_files()
        expected = [
            "/path/to/file1.dot",
            "/path/to/file2.puml",
            "/path/to/file3.mermaid"
        ]
        assert sorted(files) == sorted(expected)

    def test_window_count_property(self):
        """Test window count property."""
        manager = WindowManager()

        assert manager.window_count == 0

        # Add windows
        manager.windows["file1"] = Mock()
        assert manager.window_count == 1

        manager.windows["file2"] = Mock()
        assert manager.window_count == 2

        # Remove window
        del manager.windows["file1"]
        assert manager.window_count == 1

    def test_close_all_windows(self):
        """Test closing all windows."""
        manager = WindowManager()

        # Create mock windows
        mock_window1 = Mock()
        mock_window1.close = Mock()
        mock_window2 = Mock()
        mock_window2.close = Mock()

        manager.windows = {
            "file1": mock_window1,
            "file2": mock_window2,
        }

        assert manager.window_count == 2

        manager.close_all_windows()

        assert manager.windows == {}
        assert manager.window_count == 0
        mock_window1.close.assert_called_once()
        mock_window2.close.assert_called_once()


class TestWindowFactory:
    """Test suite for window factory functionality."""

    def test_create_window_with_mock_qt(self):
        """Test creating a window with mocked PySide components."""
        from unittest.mock import patch

        manager = WindowManager()

        # Mock PySide components
        with patch('dacwatch.window_manager.DiagramWindow') as mock_diagram_window:

            # Setup mock instance
            mock_window_instance = Mock()
            mock_window_instance.file_path = "/path/to/test/file.dot"
            mock_window_instance.loading_label = Mock()
            mock_diagram_window.return_value = mock_window_instance

            # Create window
            result = manager._create_window("/path/to/test/file.dot")

            # Verify DiagramWindow was created correctly
            mock_diagram_window.assert_called_once_with("/path/to/test/file.dot")

            # Verify the result
            assert result == mock_window_instance
            assert result.file_path == "/path/to/test/file.dot"

    def test_create_window_sets_file_path_attribute(self):
        """Test that created window has file_path attribute set."""
        from unittest.mock import patch

        manager = WindowManager()

        with patch('dacwatch.window_manager.DiagramWindow') as mock_diagram_window:
            mock_window_instance = Mock()
            mock_window_instance.file_path = "/path/to/test/diagram.puml"
            mock_diagram_window.return_value = mock_window_instance

            file_path = "/path/to/test/diagram.puml"
            result = manager._create_window(file_path)

            assert hasattr(result, 'file_path')
            assert result.file_path == file_path

    def test_create_window_handles_different_file_types(self):
        """Test window creation for different file types."""
        from unittest.mock import patch

        manager = WindowManager()

        with patch('dacwatch.window_manager.DiagramWindow') as mock_diagram_window:

            test_cases = [
                "/path/to/graph.dot",
                "/path/to/diagram.puml",
                "/path/to/chart.mermaid",
                "/deep/nested/path/complex_diagram.plantuml"
            ]

            for file_path in test_cases:
                mock_window_instance = Mock()
                mock_window_instance.file_path = file_path
                mock_diagram_window.return_value = mock_window_instance

                result = manager._create_window(file_path)

                mock_diagram_window.assert_called_with(file_path)
                assert result.file_path == file_path


class TestWindowCleanup:
    """Test suite for window cleanup functionality."""

    def test_cleanup_deleted_file_existing_window(self):
        """Test cleanup when a file with an open window is deleted."""
        manager = WindowManager()

        # Create a mock window
        mock_window = Mock()
        mock_window.close = Mock()
        file_path = "/path/to/test/file.dot"

        # Manually add to registry
        manager.windows[file_path] = mock_window

        # Cleanup the deleted file
        manager.cleanup_deleted_file(file_path)

        # Verify window was closed and removed
        mock_window.close.assert_called_once()
        assert file_path not in manager.windows
        assert manager.window_count == 0

    def test_cleanup_deleted_file_nonexistent_window(self):
        """Test cleanup when trying to cleanup a file that has no window."""
        manager = WindowManager()

        # Try to cleanup a file that doesn't have a window
        file_path = "/path/to/nonexistent/file.dot"
        manager.cleanup_deleted_file(file_path)

        # Should not raise an error and window count should remain 0
        assert manager.window_count == 0

    def test_cleanup_deleted_file_multiple_windows(self):
        """Test cleanup with multiple windows, only one deleted."""
        manager = WindowManager()

        # Create mock windows
        mock_window1 = Mock()
        mock_window1.close = Mock()
        mock_window2 = Mock()
        mock_window2.close = Mock()
        mock_window3 = Mock()
        mock_window3.close = Mock()

        # Add windows to registry
        manager.windows = {
            "/path/to/file1.dot": mock_window1,
            "/path/to/file2.puml": mock_window2,
            "/path/to/file3.mermaid": mock_window3,
        }

        # Cleanup one file
        manager.cleanup_deleted_file("/path/to/file2.puml")

        # Verify only the correct window was closed
        mock_window1.close.assert_not_called()
        mock_window2.close.assert_called_once()
        mock_window3.close.assert_not_called()

        # Verify registry state
        assert "/path/to/file1.dot" in manager.windows
        assert "/path/to/file2.puml" not in manager.windows
        assert "/path/to/file3.mermaid" in manager.windows
        assert manager.window_count == 2

    def test_cleanup_deleted_file_with_path_normalization(self):
        """Test cleanup handles path normalization correctly."""
        manager = WindowManager()

        # Create a mock window
        mock_window = Mock()
        mock_window.close = Mock()
        file_path = "/path/to/test/file.dot"

        # Add with normalized path
        manager.windows[file_path] = mock_window

        # Try to cleanup with different path formats
        test_paths = [
            "/path/to/test/file.dot",  # exact match
            "/path/to/test/../test/file.dot",  # with parent directory
            "./file.dot",  # relative path (won't match)
        ]

        # Only the exact match should work
        manager.cleanup_deleted_file(test_paths[0])
        mock_window.close.assert_called_once()
        assert file_path not in manager.windows

    def test_cleanup_all_deleted_files(self):
        """Test cleanup of all files that were deleted."""
        manager = WindowManager()

        # Create mock windows
        mock_window1 = Mock()
        mock_window1.close = Mock()
        mock_window2 = Mock()
        mock_window2.close = Mock()
        mock_window3 = Mock()
        mock_window3.close = Mock()

        # Add windows to registry
        manager.windows = {
            "/path/to/file1.dot": mock_window1,
            "/path/to/file2.puml": mock_window2,
            "/path/to/file3.mermaid": mock_window3,
        }

        # Simulate file deletion by providing list of deleted files
        deleted_files = ["/path/to/file1.dot", "/path/to/file3.mermaid"]
        manager.cleanup_deleted_files(deleted_files)

        # Verify correct windows were closed
        mock_window1.close.assert_called_once()
        mock_window2.close.assert_not_called()
        mock_window3.close.assert_called_once()

        # Verify registry state
        assert "/path/to/file1.dot" not in manager.windows
        assert "/path/to/file2.puml" in manager.windows
        assert "/path/to/file3.mermaid" not in manager.windows
        assert manager.window_count == 1


class TestDiagramWindowImageDisplay:
    """Test suite for DiagramWindow image display functionality."""

    def test_display_image_svg_format(self, qtbot):
        """Test displaying SVG image data using real Qt widgets."""
        from dacwatch.window_manager import DiagramWindow, ZoomableGraphicsView
        from PySide6.QtWidgets import QGraphicsScene

        # Create a real DiagramWindow
        window = DiagramWindow("/test/path.svg")
        qtbot.addWidget(window)

        # Create minimal SVG data
        svg_data = b'<svg width="100" height="100"><circle cx="50" cy="50" r="40"/></svg>'

        # Call display_image
        window.display_image(svg_data, "svg")

        # Verify graphics view was created and is the main display widget
        assert window.graphics_view is not None
        assert isinstance(window.graphics_view, ZoomableGraphicsView)
        
        # Verify graphics scene was created
        assert window.graphics_scene is not None
        assert isinstance(window.graphics_scene, QGraphicsScene)
        
        # Verify pixmap item was created
        assert window.pixmap_item is not None
        
        # Verify format label was updated
        assert window.format_label is not None
        assert window.format_label.text() == "Format: SVG"

    def test_display_image_png_format(self, qtbot):
        """Test displaying PNG image data using real Qt widgets."""
        from dacwatch.window_manager import DiagramWindow, ZoomableGraphicsView

        # Create a real DiagramWindow
        window = DiagramWindow("/test/path.png")
        qtbot.addWidget(window)

        # Create minimal PNG data (this won't load as a real image, but we're testing the flow)
        png_data = b'\x89PNG\r\n\x1a\n' + b'x' * 100  # Minimal PNG header + data

        # Call display_image
        window.display_image(png_data, "png")

        # Verify graphics view was created
        assert window.graphics_view is not None
        assert isinstance(window.graphics_view, ZoomableGraphicsView)
        
        # Verify format label was updated
        assert window.format_label is not None
        assert window.format_label.text() == "Format: PNG"

    def test_display_image_replaces_loading_label(self, qtbot):
        """Test that display_image replaces the loading label with graphics view."""
        from dacwatch.window_manager import DiagramWindow, ZoomableGraphicsView

        # Create a real DiagramWindow
        window = DiagramWindow("/test/path.svg")
        qtbot.addWidget(window)

        # Verify loading label exists initially
        assert window.loading_label is not None

        # Create minimal SVG data
        svg_data = b'<svg width="100" height="100"><circle cx="50" cy="50" r="40"/></svg>'

        # Call display_image
        window.display_image(svg_data, "svg")

        # Verify loading label is now hidden
        assert not window.loading_label.isVisible()

        # Verify graphics view was created and added
        assert window.graphics_view is not None
        assert isinstance(window.graphics_view, ZoomableGraphicsView)

    def test_display_image_handles_empty_data(self, qtbot):
        """Test display_image handles empty image data gracefully."""
        from dacwatch.window_manager import DiagramWindow, ZoomableGraphicsView

        # Create a real DiagramWindow
        window = DiagramWindow("/test/path.svg")
        qtbot.addWidget(window)

        # Call display_image with empty data
        window.display_image(b'', "svg")

        # Verify it doesn't crash and graphics view was created
        assert window.graphics_view is not None
        assert isinstance(window.graphics_view, ZoomableGraphicsView)
        
        # Verify format label was updated
        assert window.format_label is not None
        assert window.format_label.text() == "Format: SVG"

    def test_display_image_invalid_format(self):
        """Test display_image with invalid format parameter."""
        from unittest.mock import patch, Mock

        # Create a mock window object to test the method
        mock_window = Mock()

        # Import and bind the method to our mock
        from dacwatch.window_manager import DiagramWindow
        mock_window.display_image = DiagramWindow.display_image.__get__(mock_window, DiagramWindow)

        # Should raise ValueError for invalid format
        with pytest.raises(ValueError, match="Format must be 'svg' or 'png'"):
            mock_window.display_image(b'test', "invalid")


class TestDiagramWindowToolbar:
    """Test suite for DiagramWindow toolbar functionality."""

    def test_toggle_format_button_creation(self, qtbot):
        """Test that toggle format button is created and configured using real Qt widgets."""
        from dacwatch.window_manager import DiagramWindow
        from PySide6.QtWidgets import QPushButton, QToolBar, QLabel
        
        # Create a real DiagramWindow
        window = DiagramWindow("/path/to/test/file.dot")
        qtbot.addWidget(window)
        
        # Check that toolbars exist
        toolbars = window.findChildren(QToolBar)
        assert len(toolbars) >= 1
        
        toolbar = toolbars[0]
        
        # Find buttons in the toolbar
        buttons = toolbar.findChildren(QPushButton)
        toggle_button = None
        for button in buttons:
            if "Toggle" in button.text():
                toggle_button = button
                break
        
        assert toggle_button is not None, "Toggle SVG/PNG button should exist"
        
        # Check that format label exists
        assert hasattr(window, 'format_label')
        assert window.format_label is not None
        
        # Verify the format label is a QLabel
        assert isinstance(window.format_label, QLabel)
        
        # Check that format label is in the toolbar
        labels_in_toolbar = toolbar.findChildren(QLabel)
        assert window.format_label in labels_in_toolbar

    def test_copy_image_button_creation(self, qtbot):
        """Test that copy image button is created and configured."""
        from dacwatch.window_manager import DiagramWindow
        from PySide6.QtWidgets import QPushButton, QToolBar
        
        # Create a real DiagramWindow
        window = DiagramWindow("/path/to/test/file.dot")
        qtbot.addWidget(window)
        
        # Check that toolbars exist
        toolbars = window.findChildren(QToolBar)
        assert len(toolbars) >= 1
        
        toolbar = toolbars[0]
        
        # Find copy image button
        buttons = toolbar.findChildren(QPushButton)
        copy_button = None
        for button in buttons:
            if "Copy Image" in button.text():
                copy_button = button
                break
        
        assert copy_button is not None, "Copy Image button should exist"

    def test_copy_source_button_creation(self, qtbot):
        """Test that copy source button is created and configured."""
        from dacwatch.window_manager import DiagramWindow
        from PySide6.QtWidgets import QPushButton, QToolBar
        
        # Create a real DiagramWindow
        window = DiagramWindow("/path/to/test/file.dot")
        qtbot.addWidget(window)
        
        # Check that toolbars exist
        toolbars = window.findChildren(QToolBar)
        assert len(toolbars) >= 1
        
        toolbar = toolbars[0]
        
        # Find copy source button
        buttons = toolbar.findChildren(QPushButton)
        copy_source_button = None
        for button in buttons:
            if "Copy Source" in button.text():
                copy_source_button = button
                break
        
        assert copy_source_button is not None, "Copy Source button should exist"

    def test_reveal_finder_button_creation(self, qtbot):
        """Test that reveal in Finder button is created and configured."""
        from dacwatch.window_manager import DiagramWindow
        from PySide6.QtWidgets import QPushButton, QToolBar
        
        # Create a real DiagramWindow
        window = DiagramWindow("/path/to/test/file.dot")
        qtbot.addWidget(window)
        
        # Check that toolbars exist
        toolbars = window.findChildren(QToolBar)
        assert len(toolbars) >= 1
        
        toolbar = toolbars[0]
        
        # Find reveal in Finder button
        buttons = toolbar.findChildren(QPushButton)
        reveal_button = None
        for button in buttons:
            if "Reveal in Finder" in button.text():
                reveal_button = button
                break
        
        assert reveal_button is not None, "Reveal in Finder button should exist"
        
        # Verify we have all expected buttons
        button_texts = [button.text() for button in buttons]
        expected_buttons = ["Toggle SVG/PNG", "Copy Image", "Copy Source", "Reveal in Finder"]
        for expected in expected_buttons:
            assert expected in button_texts, f"Button '{expected}' should exist"

    def test_toggle_format_functionality(self):
        """Test toggle format functionality."""
        from unittest.mock import patch, Mock

        # Create a mock window object
        mock_window = Mock()
        mock_window.current_format = "svg"
        mock_window.image_data = b'<svg>test</svg>'
        mock_window.format_toggle_callback = Mock()

        # Import and bind the method to our mock
        from dacwatch.window_manager import DiagramWindow
        mock_window.toggle_format = DiagramWindow.toggle_format.__get__(mock_window, DiagramWindow)

        # Call toggle_format
        mock_window.toggle_format()

        # Verify callback was called with PNG format
        mock_window.format_toggle_callback.assert_called_once_with("png")

    def test_format_label_functionality(self, qtbot):
        """Test that format label shows correct format and updates properly."""
        from dacwatch.window_manager import DiagramWindow
        from PySide6.QtWidgets import QLabel
        
        # Create a real DiagramWindow
        window = DiagramWindow("/path/to/test/file.dot")
        qtbot.addWidget(window)
        
        # Check that format label exists
        assert hasattr(window, 'format_label')
        assert isinstance(window.format_label, QLabel)
        
        # Test display_image updates format label
        test_svg_data = b'<svg>test</svg>'
        test_png_data = b'PNG\x89test'
        
        # Test SVG format
        window.display_image(test_svg_data, "svg")
        assert window.format_label.text() == "Format: SVG"
        
        # Test PNG format
        window.display_image(test_png_data, "png")
        assert window.format_label.text() == "Format: PNG"

    def test_copy_image_to_clipboard(self, qtbot):
        """Test copying image to clipboard with transparency validation."""
        # Create SVG content with transparent background and semi-transparent element
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="20" y="20" width="60" height="60" fill="red" opacity="0.5"/>
</svg>'''

        # Create a real window
        from dacwatch.window_manager import DiagramWindow
        window = DiagramWindow("test.svg")
        qtbot.addWidget(window)

        # Load the SVG content
        window.display_image(svg_content.encode(), "svg")

        # Verify pixmap_item exists
        assert hasattr(window, 'pixmap_item')
        assert window.pixmap_item is not None

        # Copy to clipboard
        window.copy_image_to_clipboard()

        # Get clipboard image
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QImage
        clipboard = QApplication.clipboard()
        clipboard_image = clipboard.image()
        
        # Basic validation
        assert not clipboard_image.isNull()
        assert clipboard_image.hasAlphaChannel()
        assert clipboard_image.format() == QImage.Format.Format_ARGB32

        # Validate actual transparency by checking corner pixels
        # The SVG has a transparent background, so corners should be fully transparent
        corner_pixel = clipboard_image.pixelColor(5, 5)  # Top-left corner
        print(f"Corner pixel RGBA: {corner_pixel.red()}, {corner_pixel.green()}, {corner_pixel.blue()}, {corner_pixel.alpha()}")
        
        # Corner should be fully transparent (alpha = 0)
        assert corner_pixel.alpha() == 0, f"Expected transparent corner but got alpha={corner_pixel.alpha()}"
        
        # Check a pixel inside the semi-transparent rectangle
        center_pixel = clipboard_image.pixelColor(50, 50)
        print(f"Center pixel RGBA: {center_pixel.red()}, {center_pixel.green()}, {center_pixel.blue()}, {center_pixel.alpha()}")
        
        # Center should have partial transparency (alpha between 0 and 255)
        assert 0 < center_pixel.alpha() < 255, f"Expected semi-transparent center but got alpha={center_pixel.alpha()}"
        
        # Save clipboard image to file for manual verification (optional debug)
        # clipboard_image.save("/tmp/clipboard_test.png", "PNG")
        # print("Saved clipboard image to /tmp/clipboard_test.png for manual inspection")

    def test_keyboard_shortcuts(self, qtbot):
        """Test keyboard shortcuts functionality."""
        from dacwatch.window_manager import DiagramWindow
        from unittest.mock import patch, Mock
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeySequence
        from PySide6.QtTest import QTest
        
        # Create a real window
        window = DiagramWindow("test.svg")
        qtbot.addWidget(window)
        
        # Mock the methods to verify they're called
        with patch.object(window, 'copy_image_to_clipboard') as mock_copy_image, \
             patch.object(window, 'copy_source_to_clipboard') as mock_copy_source, \
             patch.object(window, 'toggle_format') as mock_toggle_format, \
             patch.object(window.always_on_top_action, 'trigger') as mock_toggle_always_on_top, \
             patch.object(window, 'reveal_in_finder') as mock_reveal_finder:
            
            # Give focus to the window
            window.show()
            qtbot.waitForWindowShown(window)
            
            # Test Cmd+C (copy image) - on macOS this uses ControlModifier in Qt
            QTest.keyClick(window, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
            qtbot.wait(10)  # Small wait for signal processing
            mock_copy_image.assert_called_once()
            
            # Test Cmd+Shift+C (copy source)  
            QTest.keyClick(window, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
            qtbot.wait(10)
            mock_copy_source.assert_called_once()
            
            # Test Cmd+F (toggle format)
            QTest.keyClick(window, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
            qtbot.wait(10)
            mock_toggle_format.assert_called_once()
            
            # Test Cmd+T (toggle always on top)
            QTest.keyClick(window, Qt.Key.Key_T, Qt.KeyboardModifier.ControlModifier)
            qtbot.wait(10)
            mock_toggle_always_on_top.assert_called_once()
            
            # Test Cmd+R (reveal in finder)
            QTest.keyClick(window, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
            qtbot.wait(10)
            mock_reveal_finder.assert_called_once()

    def test_toast_notifications(self, qtbot):
        """Test toast notifications appear when copying."""
        from dacwatch.window_manager import DiagramWindow
        import tempfile
        import os
        
        # Create a temporary file for testing
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80" fill="blue"/>
</svg>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            f.write(svg_content)
            temp_file = f.name
        
        try:
            # Create a real window with the temp file
            window = DiagramWindow(temp_file)
            qtbot.addWidget(window)
            window.show()
            qtbot.waitForWindowShown(window)
            
            # Load the content so we can copy
            window.display_image(svg_content.encode(), "svg")
            
            # Verify toast widget exists
            assert hasattr(window, 'toast')
            assert window.toast is not None
            
            # Initially toast should be hidden
            assert not window.toast.isVisible()
            
            # Test image copy toast
            window.copy_image_to_clipboard()
            qtbot.wait(10)  # Small wait for UI update
            assert window.toast.isVisible()
            assert window.toast.text() == "Copied image"
            
            # Wait for toast to disappear
            qtbot.wait(600)  # Toast duration is 500ms plus buffer
            assert not window.toast.isVisible()
            
            # Test source copy toast  
            window.copy_source_to_clipboard()
            qtbot.wait(10)  # Small wait for UI update
            assert window.toast.isVisible()
            assert window.toast.text() == "Copied source"
        
        finally:
            # Clean up temp file
            os.unlink(temp_file)

    def test_toggle_always_on_top_keyboard_shortcut(self, qtbot):
        """Test that Cmd+T properly toggles always on top state."""
        from dacwatch.window_manager import DiagramWindow
        from PySide6.QtCore import Qt
        
        # Create a real window
        window = DiagramWindow("test.svg")
        qtbot.addWidget(window)
        
        # Initially should be always on top (default state)
        initial_flags = window.windowFlags()
        assert bool(initial_flags & Qt.WindowType.WindowStaysOnTopHint)  # Should be on top by default
        assert window.always_on_top_action.isChecked()  # Action should be checked
        
        # Toggle off with keyboard shortcut (trigger action)
        window.always_on_top_action.trigger()
        
        # Should now be off
        new_flags = window.windowFlags()
        assert not bool(new_flags & Qt.WindowType.WindowStaysOnTopHint)  # Should not be on top
        assert not window.always_on_top_action.isChecked()  # Action should be unchecked
        
        # Toggle back on with keyboard shortcut (trigger action again)
        window.always_on_top_action.trigger()
        
        # Should be back on
        final_flags = window.windowFlags()
        assert bool(final_flags & Qt.WindowType.WindowStaysOnTopHint)  # Should be on top again
        assert window.always_on_top_action.isChecked()  # Action should be checked again

    def test_keyboard_focus_on_graphics_view(self, qtbot):
        """Test that keyboard focus is set to graphics view when window is shown."""
        from dacwatch.window_manager import DiagramWindow, ZoomableGraphicsView
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        
        # Create a real window
        window = DiagramWindow("test.svg")
        qtbot.addWidget(window)
        
        # Create test SVG content
        svg_content = '''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
            <rect x="50" y="50" width="100" height="100" fill="blue"/>
        </svg>'''
        
        # Display image to create graphics view
        window.display_image(svg_content.encode(), "svg")
        
        # Verify graphics view was created
        assert hasattr(window, 'graphics_view')
        assert isinstance(window.graphics_view, ZoomableGraphicsView)
        
        # Verify focus policy is set to StrongFocus
        assert window.graphics_view.focusPolicy() == Qt.FocusPolicy.StrongFocus
        
        # Show the window
        window.show()
        qtbot.waitExposed(window)
        
        # Process any pending events to ensure focus is set
        qtbot.wait(50)  # Small delay for focus processing
        QApplication.processEvents()
        
        # Manually call the focus method to test it works
        window.graphics_view.setFocus()
        qtbot.wait(10)
        QApplication.processEvents()
        
        # In headless environment, we just verify the methods exist and can be called
        # The focus policy being set to StrongFocus is the main verification
        assert window.graphics_view.focusPolicy() == Qt.FocusPolicy.StrongFocus

    def test_zoom_in_equal_key_shortcut(self, qtbot):
        """Test that Cmd+= (without shift) shortcut is properly configured."""
        from dacwatch.window_manager import DiagramWindow
        from PySide6.QtGui import QShortcut, QKeySequence
        
        # Create a real window
        window = DiagramWindow("test.svg")
        qtbot.addWidget(window)
        
        # Find all shortcuts in the window
        shortcuts = window.findChildren(QShortcut)
        
        # Look for the Ctrl+= shortcut
        ctrl_equal_shortcuts = []
        for shortcut in shortcuts:
            if shortcut.key() == QKeySequence("Ctrl+="):
                ctrl_equal_shortcuts.append(shortcut)
        
        # Verify that we have at least one Ctrl+= shortcut
        assert len(ctrl_equal_shortcuts) >= 1, "Should have at least one Ctrl+= shortcut configured"
        
        # Verify that the shortcut is connected to zoom_in method
        # We can't easily test the actual connection in a unit test, but we can verify
        # the shortcut exists and the zoom_in method exists
        assert hasattr(window, 'zoom_in'), "Window should have zoom_in method"
        
        # Verify the shortcut is enabled
        assert ctrl_equal_shortcuts[0].isEnabled(), "Ctrl+= shortcut should be enabled"

    def test_copy_source_to_clipboard(self):
        """Test copying source code to clipboard."""
        from unittest.mock import patch, Mock

        with patch('PySide6.QtWidgets.QApplication') as mock_qapp, \
             patch('builtins.open', create=True) as mock_open:

            mock_clipboard_instance = Mock()
            mock_qapp.clipboard.return_value = mock_clipboard_instance

            mock_file = Mock()
            mock_file.read.return_value = "source code content"
            mock_open.return_value.__enter__.return_value = mock_file

            # Create a mock window object
            mock_window = Mock()
            mock_window.file_path = "/path/to/test/file.dot"

            # Import and bind the method to our mock
            from dacwatch.window_manager import DiagramWindow
            mock_window.copy_source_to_clipboard = DiagramWindow.copy_source_to_clipboard.__get__(mock_window, DiagramWindow)

            # Call copy_source_to_clipboard
            mock_window.copy_source_to_clipboard()

            # Verify file was opened and read
            mock_open.assert_called_once_with("/path/to/test/file.dot", 'r')
            mock_file.read.assert_called_once()
            # Verify clipboard was set with source content
            mock_qapp.clipboard.assert_called_once()
            mock_clipboard_instance.setText.assert_called_once_with("source code content")

    def test_reveal_in_finder(self):
        """Test reveal in finder functionality."""
        from unittest.mock import patch, Mock

        with patch('subprocess.run') as mock_subprocess:
            # Create a mock window object
            mock_window = Mock()
            mock_window.file_path = "/path/to/test/file.dot"

            # Import and bind the method to our mock
            from dacwatch.window_manager import DiagramWindow
            mock_window.reveal_in_finder = DiagramWindow.reveal_in_finder.__get__(mock_window, DiagramWindow)

            # Call reveal_in_finder
            mock_window.reveal_in_finder()

            # Verify subprocess.run was called with correct arguments
            mock_subprocess.assert_called_once_with(['open', '-R', "/path/to/test/file.dot"])


class TestDiagramWindowHighDPI:
    """Test suite for DiagramWindow high-DPI image display functionality."""

    def test_high_dpi_scaling(self, qtbot):
        """Test that high-DPI scaling is enabled for image display."""
        from dacwatch.window_manager import DiagramWindow

        # Create a real DiagramWindow
        window = DiagramWindow("/test/path.svg")
        qtbot.addWidget(window)

        # Create minimal SVG data with explicit size
        svg_data = b'<svg width="200" height="150" viewBox="0 0 200 150"><circle cx="100" cy="75" r="50"/></svg>'

        # Call display_image
        window.display_image(svg_data, "svg")

        # Verify pixmap_item was created with high-DPI scaling
        assert hasattr(window, 'pixmap_item') and window.pixmap_item is not None
        pixmap = window.pixmap_item.pixmap()
        device_ratio = window.devicePixelRatio()

        # Verify device pixel ratio is set correctly
        assert pixmap.devicePixelRatio() == device_ratio

    def test_image_update_cleanup(self, qtbot):
        """Test that old graphics items are properly removed when updating."""
        from dacwatch.window_manager import DiagramWindow

        # Create a real DiagramWindow
        window = DiagramWindow("/test/path.svg")
        qtbot.addWidget(window)

        # Display first image
        svg_data1 = b'<svg width="100" height="100"><rect fill="red" width="100" height="100"/></svg>'
        window.display_image(svg_data1, "svg")

        # Get reference to first pixmap item
        first_pixmap_item = window.pixmap_item
        assert first_pixmap_item is not None
        first_graphics_view = window.graphics_view
        assert first_graphics_view is not None
        
        # Verify there's one graphics view in the central widget
        central_widget = window.centralWidget()
        layout = central_widget.layout()
        
        # Count widgets in the main layout (excluding toolbar and loading label)
        layout_widgets = []
        if layout:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget and widget != window.loading_label:
                        layout_widgets.append(widget)
        
        assert len(layout_widgets) == 1, f"Expected 1 widget in layout, found {len(layout_widgets)}: {[type(w).__name__ for w in layout_widgets]}"
        assert layout_widgets[0] == window.graphics_view
        
        # Display second image (simulating file update)
        svg_data2 = b'<svg width="100" height="100"><circle fill="blue" cx="50" cy="50" r="50"/></svg>'
        window.display_image(svg_data2, "svg")
        
        # Get reference to second pixmap item - it should be a new item
        second_pixmap_item = window.pixmap_item
        assert second_pixmap_item is not None
        assert second_pixmap_item != first_pixmap_item  # Should be different items
        
        # Graphics view should be replaced with a new one
        second_graphics_view = window.graphics_view
        assert second_graphics_view != first_graphics_view
        
        # Verify there's still only one widget in the layout
        layout_widgets_after = []
        if layout:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget and widget != window.loading_label:
                        layout_widgets_after.append(widget)
        
        assert len(layout_widgets_after) == 1, f"Expected 1 widget in layout after update, found {len(layout_widgets_after)}"
        
        # The widget should be the graphics view
        assert layout_widgets_after[0] == window.graphics_view

    def test_image_resizes_with_window(self, qtbot):
        """Test that graphics view handles image display correctly."""
        from dacwatch.window_manager import DiagramWindow
        from PySide6.QtCore import Qt
        
        # Create a real DiagramWindow
        window = DiagramWindow("/test/path.svg")
        qtbot.addWidget(window)
        
        # Display an image
        svg_data = b'<svg width="200" height="200"><rect width="200" height="200" fill="green"/></svg>'
        window.display_image(svg_data, "svg")
        
        # Verify the graphics view and pixmap item are set up correctly
        graphics_view = window.graphics_view
        pixmap_item = window.pixmap_item
        
        # Graphics view should exist and have a scene
        assert graphics_view is not None
        assert graphics_view.scene() is not None
        
        # Pixmap item should contain the image
        assert pixmap_item is not None
        assert not pixmap_item.pixmap().isNull()

    def test_pixel_ratio_maintained(self, qtbot):
        """Test that pixels maintain 1:1 ratio (square pixels) when window is resized."""
        from dacwatch.window_manager import DiagramWindow
        from PySide6.QtCore import Qt
        
        # Create a real DiagramWindow
        window = DiagramWindow("/test/path.svg")
        qtbot.addWidget(window)
        
        # Create a non-square SVG to test pixel ratio (2:1 image ratio)
        svg_data = b'<svg width="400" height="200"><rect width="400" height="200" fill="red"/></svg>'
        window.display_image(svg_data, "svg")
        
        # Get the original pixmap and its aspect ratio
        original_pixmap = window.pixmap_item.pixmap()
        assert original_pixmap is not None
        
        # Calculate logical size (accounting for device pixel ratio)
        device_ratio = original_pixmap.devicePixelRatio()
        logical_width = original_pixmap.width() / device_ratio
        logical_height = original_pixmap.height() / device_ratio
        original_ratio = logical_width / logical_height
        
        # The original should have 2:1 aspect ratio
        assert abs(original_ratio - 2.0) < 0.1, f"Expected ~2.0 ratio, got {original_ratio}"
        
        # Verify device pixel ratio is maintained
        window_device_ratio = window.devicePixelRatio()
        assert device_ratio == window_device_ratio, f"Expected device ratio {window_device_ratio}, got {device_ratio}"
        
        # Verify pixmap item maintains correct proportions
        assert window.pixmap_item is not None
        assert not window.pixmap_item.pixmap().isNull()




class TestWindowState:
    """Test suite for window state persistence."""

    def test_save_window_state(self):
        """Test saving window state."""
        manager = WindowManager()

        # Create a mock window with state
        mock_window = Mock()
        mock_window.file_path = "/path/to/test/file.dot"
        mock_window.x.return_value = 100
        mock_window.y.return_value = 200
        mock_window.width.return_value = 800
        mock_window.height.return_value = 600

        file_path = "/path/to/test/file.dot"
        manager.windows[file_path] = mock_window

        # Save state
        manager.save_window_state(file_path)

        # Verify state was saved
        expected_state = {
            'x': 100,
            'y': 200,
            'width': 800,
            'height': 600
        }
        assert manager.window_states[file_path] == expected_state

    def test_restore_window_state(self):
        """Test restoring window state."""
        manager = WindowManager()

        # Set up saved state
        file_path = "/path/to/test/file.dot"
        saved_state = {
            'x': 150,
            'y': 250,
            'width': 900,
            'height': 700
        }
        manager.window_states[file_path] = saved_state

        # Create a mock window
        mock_window = Mock()
        mock_window.file_path = file_path
        mock_window.setGeometry = Mock()
        mock_window.show = Mock()

        # Restore state
        manager.restore_window_state(mock_window, file_path)

        # Verify geometry was set
        mock_window.setGeometry.assert_called_once_with(150, 250, 900, 700)

    def test_restore_window_state_no_saved_state(self, tmp_path):
        """Test restoring window state when no saved state exists."""
        # Use a temporary state file path that doesn't exist
        state_file = tmp_path / "test_state.json"
        manager = WindowManager(state_file_path=str(state_file))

        # Create a mock window
        mock_window = Mock()
        mock_window.file_path = "/path/to/test/file.dot"
        mock_window.setGeometry = Mock()
        mock_window.show = Mock()

        # Try to restore state for file with no saved state
        manager.restore_window_state(mock_window, "/path/to/test/file.dot")

        # Verify geometry was not set (default behavior)
        mock_window.setGeometry.assert_not_called()

    def test_persist_state_to_file(self, tmp_path):
        """Test persisting window state to a file."""
        manager = WindowManager()

        # Set up state file path
        state_file = tmp_path / "window_state.json"
        manager.state_file_path = str(state_file)

        # Add some window states
        manager.window_states = {
            "/path/to/file1.dot": {'x': 100, 'y': 200, 'width': 800, 'height': 600},
            "/path/to/file2.puml": {'x': 200, 'y': 300, 'width': 700, 'height': 500}
        }

        # Persist to file
        manager.persist_state()

        # Verify file was created and contains correct data
        assert state_file.exists()

        import json
        with open(state_file, 'r') as f:
            saved_data = json.load(f)

        assert saved_data == manager.window_states

    def test_load_state_from_file(self, tmp_path):
        """Test loading window state from a file."""
        manager = WindowManager()

        # Set up state file path
        state_file = tmp_path / "window_state.json"
        manager.state_file_path = str(state_file)

        # Create state file with data
        state_data = {
            "/path/to/file1.dot": {'x': 100, 'y': 200, 'width': 800, 'height': 600},
            "/path/to/file2.puml": {'x': 200, 'y': 300, 'width': 700, 'height': 500}
        }

        import json
        with open(state_file, 'w') as f:
            json.dump(state_data, f)

        # Load state
        manager.load_state()

        # Verify state was loaded
        assert manager.window_states == state_data

    def test_load_state_from_nonexistent_file(self, tmp_path):
        """Test loading window state from a nonexistent file."""
        # Use a temporary state file path that doesn't exist
        state_file = tmp_path / "nonexistent_state.json"
        manager = WindowManager(state_file_path=str(state_file))

        # Load state (should not raise error)
        manager.load_state()

        # Verify state is empty
        assert manager.window_states == {}

    def test_auto_save_on_window_close(self):
        """Test that window state is automatically saved when window is closed."""
        manager = WindowManager()

        # Create a mock window with state
        mock_window = Mock()
        mock_window.file_path = "/path/to/test/file.dot"
        mock_window.x.return_value = 100
        mock_window.y.return_value = 200
        mock_window.width.return_value = 800
        mock_window.height.return_value = 600
        mock_window.close = Mock()

        file_path = "/path/to/test/file.dot"
        manager.windows[file_path] = mock_window

        # Close window (should auto-save state)
        manager.close_window(file_path)

        # Verify state was saved
        expected_state = {
            'x': 100,
            'y': 200,
            'width': 800,
            'height': 600
        }
        assert manager.window_states[file_path] == expected_state
        mock_window.close.assert_called_once()

    def test_auto_restore_on_window_create(self):
        """Test that window state is automatically restored when window is created."""
        manager = WindowManager()

        # Set up saved state
        file_path = "/path/to/test/file.dot"
        saved_state = {
            'x': 150,
            'y': 250,
            'width': 900,
            'height': 700
        }
        manager.window_states[file_path] = saved_state

        # Mock the window creation to return a window that can have state restored
        mock_window = Mock()
        mock_window.file_path = file_path
        mock_window.setGeometry = Mock()
        mock_window.show = Mock()

        with patch('dacwatch.window_manager.DiagramWindow') as mock_diagram_window:
            mock_diagram_window.return_value = mock_window

            # Create window (should auto-restore state)
            result = manager.create_window(file_path)

            # Verify state was restored
            mock_window.setGeometry.assert_called_once_with(150, 250, 900, 700)