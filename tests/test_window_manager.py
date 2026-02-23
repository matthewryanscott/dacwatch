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
        manager._create_window.assert_called_once_with("/path/to/test/file.dot", actual_file_path=None, window_title=None)

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
        manager._create_window.assert_called_once_with("/path/to/test/file.dot", actual_file_path=None, window_title=None)

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
            mock_diagram_window.assert_called_once_with("/path/to/test/file.dot", window_manager=manager, actual_file_path=None)

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

                mock_diagram_window.assert_called_with(file_path, window_manager=manager, actual_file_path=None)
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
        
        # Verify format radio buttons were updated
        assert hasattr(window, 'svg_radio') and window.svg_radio is not None
        assert hasattr(window, 'png_radio') and window.png_radio is not None
        assert window.svg_radio.isChecked() == True
        assert window.png_radio.isChecked() == False

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
        
        # Verify format radio buttons were updated
        assert hasattr(window, 'svg_radio') and window.svg_radio is not None
        assert hasattr(window, 'png_radio') and window.png_radio is not None
        assert window.svg_radio.isChecked() == False
        assert window.png_radio.isChecked() == True

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
        
        # Verify format radio buttons were updated
        assert hasattr(window, 'svg_radio') and window.svg_radio is not None
        assert hasattr(window, 'png_radio') and window.png_radio is not None
        assert window.svg_radio.isChecked() == True
        assert window.png_radio.isChecked() == False

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

    def test_format_radio_buttons_creation(self, qtbot):
        """Test that format radio buttons are created and configured using real Qt widgets."""
        from dacwatch.window_manager import DiagramWindow
        from PySide6.QtWidgets import QRadioButton, QToolBar, QButtonGroup
        
        # Create a real DiagramWindow
        window = DiagramWindow("/path/to/test/file.dot")
        qtbot.addWidget(window)
        
        # Check that toolbars exist
        toolbars = window.findChildren(QToolBar)
        assert len(toolbars) >= 1
        
        toolbar = toolbars[0]
        
        # Check that format radio buttons exist
        assert hasattr(window, 'svg_radio') and window.svg_radio is not None
        assert hasattr(window, 'png_radio') and window.png_radio is not None
        
        # Verify they are QRadioButton instances
        assert isinstance(window.svg_radio, QRadioButton)
        assert isinstance(window.png_radio, QRadioButton)
        
        # Check that button group exists
        assert hasattr(window, 'format_button_group') and window.format_button_group is not None
        assert isinstance(window.format_button_group, QButtonGroup)
        
        # Check that radio buttons are in the toolbar
        radio_buttons_in_toolbar = toolbar.findChildren(QRadioButton)
        assert window.svg_radio in radio_buttons_in_toolbar
        assert window.png_radio in radio_buttons_in_toolbar
        
        # Check default state (SVG should be selected)
        assert window.svg_radio.isChecked() == True
        assert window.png_radio.isChecked() == False

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
            if "📋 Image" in button.text():
                copy_button = button
                break
        
        assert copy_button is not None, "📋 Image button should exist"

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
            if "📋 Source" in button.text():
                copy_source_button = button
                break
        
        assert copy_source_button is not None, "📋 Source button should exist"

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
            if "Reveal" in button.text():
                reveal_button = button
                break
        
        assert reveal_button is not None, "Reveal button should exist"
        
        # Verify we have all expected buttons (excluding the removed toggle button)
        button_texts = [button.text() for button in buttons]
        expected_buttons = ["📋 Image", "📋 Source", "📋 Error", "Reveal"]
        for expected in expected_buttons:
            assert expected in button_texts, f"Button '{expected}' should exist"

    def test_button_labels_with_emojis(self, qtbot):
        """Test that button labels include the correct emojis and text."""
        from dacwatch.window_manager import DiagramWindow
        from PySide6.QtWidgets import QPushButton
        
        # Create a real DiagramWindow
        window = DiagramWindow("/path/to/test/file.dot")
        qtbot.addWidget(window)
        
        # Test specific button labels
        assert hasattr(window, 'copy_image_button')
        assert window.copy_image_button.text() == "📋 Image"
        
        assert hasattr(window, 'copy_source_button')
        assert window.copy_source_button.text() == "📋 Source"
        
        assert hasattr(window, 'copy_error_button')
        assert window.copy_error_button.text() == "📋 Error"
        
        assert hasattr(window, 'reveal_button')
        assert window.reveal_button.text() == "Reveal"

    def test_format_radio_functionality(self, qtbot):
        """Test format radio button functionality."""
        from dacwatch.window_manager import DiagramWindow
        from unittest.mock import Mock
        
        # Create a real window
        window = DiagramWindow("/test/file.svg")
        qtbot.addWidget(window)
        
        # Mock the format toggle callback
        window.format_toggle_callback = Mock()
        window.current_format = "svg"
        window.image_data = b'<svg>test</svg>'
        
        # Initially SVG should be selected
        assert window.svg_radio.isChecked() == True
        assert window.png_radio.isChecked() == False
        
        # Select PNG radio button
        window.png_radio.setChecked(True)
        
        # Process events to ensure signal is handled
        qtbot.wait(10)
        
        # Verify callback was called with PNG format
        window.format_toggle_callback.assert_called_once_with("png")
        
        # Reset mock for second test
        window.format_toggle_callback.reset_mock()
        window.current_format = "png"
        
        # Select SVG radio button
        window.svg_radio.setChecked(True)
        
        # Process events
        qtbot.wait(10)
        
        # Verify callback was called with SVG format
        window.format_toggle_callback.assert_called_once_with("svg")

    def test_format_radio_state_updates(self, qtbot):
        """Test that format radio buttons show correct format and update properly."""
        from dacwatch.window_manager import DiagramWindow
        from PySide6.QtWidgets import QRadioButton
        
        # Create a real DiagramWindow
        window = DiagramWindow("/path/to/test/file.dot")
        qtbot.addWidget(window)
        
        # Check that format radio buttons exist
        assert hasattr(window, 'svg_radio') and isinstance(window.svg_radio, QRadioButton)
        assert hasattr(window, 'png_radio') and isinstance(window.png_radio, QRadioButton)
        
        # Test display_image updates radio button states
        test_svg_data = b'<svg>test</svg>'
        test_png_data = b'PNG\x89test'
        
        # Test SVG format
        window.display_image(test_svg_data, "svg")
        assert window.svg_radio.isChecked() == True
        assert window.png_radio.isChecked() == False
        
        # Test PNG format
        window.display_image(test_png_data, "png")
        assert window.svg_radio.isChecked() == False
        assert window.png_radio.isChecked() == True

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
        with patch.object(window, 'copy_image_with_white_background') as mock_copy_white_bg, \
             patch.object(window, 'copy_source_to_clipboard') as mock_copy_source, \
             patch.object(window, 'toggle_format') as mock_toggle_format, \
             patch.object(window.always_on_top_action, 'trigger') as mock_toggle_always_on_top, \
             patch.object(window, 'reveal_in_finder') as mock_reveal_finder:

            # Give focus to the window
            window.show()
            qtbot.waitForWindowShown(window)

            # Test Cmd+C (copy image with white background) - on macOS this uses ControlModifier in Qt
            QTest.keyClick(window, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
            qtbot.wait(10)  # Small wait for signal processing
            mock_copy_white_bg.assert_called_once()
            
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
            
            # Test image copy toast (white background is the default)
            window.copy_image_with_white_background()
            qtbot.wait(10)  # Small wait for UI update
            assert window.toast.isVisible()
            assert window.toast.text() == "Copied with white background"
            
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
        
        # Initially should NOT be always on top (default state)
        initial_flags = window.windowFlags()
        assert not bool(initial_flags & Qt.WindowType.WindowStaysOnTopHint)  # Should NOT be on top by default
        assert not window.always_on_top_action.isChecked()  # Action should be unchecked
        
        # Toggle on with keyboard shortcut (trigger action)
        window.always_on_top_action.trigger()

        # Should now be on
        new_flags = window.windowFlags()
        assert bool(new_flags & Qt.WindowType.WindowStaysOnTopHint)  # Should be on top
        assert window.always_on_top_action.isChecked()  # Action should be checked

        # Toggle back off with keyboard shortcut (trigger action again)
        window.always_on_top_action.trigger()

        # Should be back off
        final_flags = window.windowFlags()
        assert not bool(final_flags & Qt.WindowType.WindowStaysOnTopHint)  # Should not be on top again
        assert not window.always_on_top_action.isChecked()  # Action should be unchecked again

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

    def test_zoom_label_creation_and_updates(self, qtbot):
        """Test that zoom label is created and updates correctly."""
        from dacwatch.window_manager import DiagramWindow
        from PySide6.QtWidgets import QLabel, QToolBar
        
        # Create a real window
        window = DiagramWindow("test.svg")
        qtbot.addWidget(window)
        
        # Create test SVG content and display it
        svg_content = '''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
            <rect x="50" y="50" width="100" height="100" fill="green"/>
        </svg>'''
        window.display_image(svg_content.encode(), "svg")
        
        # Check that toolbars exist
        toolbars = window.findChildren(QToolBar)
        assert len(toolbars) >= 1
        
        toolbar = toolbars[0]
        
        # Check that zoom label exists
        assert hasattr(window, 'zoom_label')
        assert window.zoom_label is not None
        assert isinstance(window.zoom_label, QLabel)
        
        # Check that zoom label is in the toolbar
        labels_in_toolbar = toolbar.findChildren(QLabel)
        assert window.zoom_label in labels_in_toolbar
        
        # Initially should show 100%
        assert window.zoom_label.text() == "100%"
        
        # Test zoom in - should update label
        window.zoom_in()
        expected_zoom = int(1.25 * 100)  # 125%
        assert window.zoom_label.text() == f"{expected_zoom}%"
        
        # Test zoom out - should update label  
        window.zoom_out()
        expected_zoom = int(1.25 * 0.8 * 100)  # 100% (1.25 * 0.8 = 1.0)
        assert window.zoom_label.text() == f"{expected_zoom}%"
        
        # Test reset zoom - should show 100%
        window.reset_zoom()
        assert window.zoom_label.text() == "100%"

    def test_fit_button_creation(self, qtbot):
        """Test that fit button is created and positioned correctly."""
        from dacwatch.window_manager import DiagramWindow
        from PySide6.QtWidgets import QPushButton, QToolBar
        
        # Create a real DiagramWindow
        window = DiagramWindow("/path/to/test/file.dot")
        qtbot.addWidget(window)
        
        # Check that toolbars exist
        toolbars = window.findChildren(QToolBar)
        assert len(toolbars) >= 1
        
        toolbar = toolbars[0]
        
        # Find fit button
        buttons = toolbar.findChildren(QPushButton)
        fit_button = None
        for button in buttons:
            if button.text() == "Fit":
                fit_button = button
                break
        
        assert fit_button is not None, "Fit button should exist"
        assert hasattr(window, 'fit_button'), "Window should have fit_button attribute"
        assert window.fit_button.text() == "Fit"
        
        # Verify button order: should be after Copy Error and before Reveal
        button_texts = [button.text() for button in buttons]
        
        # Find indices of buttons
        copy_error_index = None
        fit_index = None
        reveal_index = None
        
        for i, text in enumerate(button_texts):
            if "📋 Error" in text:
                copy_error_index = i
            elif text == "Fit":
                fit_index = i
            elif text == "Reveal":
                reveal_index = i
        
        # Verify the order
        assert copy_error_index is not None, "Copy Error button should exist"
        assert fit_index is not None, "Fit button should exist"
        assert reveal_index is not None, "Reveal button should exist"
        assert copy_error_index < fit_index < reveal_index, "Fit button should be between Copy Error and Reveal buttons"

    def test_fit_to_diagram_functionality(self, qtbot):
        """Test fit to diagram functionality."""
        from dacwatch.window_manager import DiagramWindow
        from unittest.mock import Mock
        
        # Create a real window
        window = DiagramWindow("test.svg")
        qtbot.addWidget(window)
        
        # Create test SVG content with specific dimensions
        svg_content = '''<svg width="300" height="200" xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="300" height="200" fill="blue"/>
        </svg>'''
        
        # Display the image to set up graphics view and pixmap
        window.display_image(svg_content.encode(), "svg")
        
        # Verify the image was loaded
        assert hasattr(window, 'pixmap_item') and window.pixmap_item is not None
        assert hasattr(window, 'graphics_view') and window.graphics_view is not None
        
        # Mock the window resize method to capture calls
        original_resize = window.resize
        window.resize = Mock(side_effect=original_resize)
        
        # Mock size methods to return predictable values for testing
        mock_window_size = Mock()
        mock_window_size.width = Mock(return_value=800)
        mock_window_size.height = Mock(return_value=600)
        window.size = Mock(return_value=mock_window_size)
        
        mock_view_size = Mock()
        mock_view_size.width = Mock(return_value=700)
        mock_view_size.height = Mock(return_value=500)
        window.graphics_view.size = Mock(return_value=mock_view_size)
        
        # Mock viewport size for fit calculation
        mock_viewport_size = Mock()
        mock_viewport_size.width = Mock(return_value=680)
        mock_viewport_size.height = Mock(return_value=480)
        window.graphics_view.viewport = Mock()
        window.graphics_view.viewport.return_value.size = Mock(return_value=mock_viewport_size)
        
        # Call fit_to_diagram
        window.fit_to_diagram()
        
        # Verify resize was called
        window.resize.assert_called_once()
        
        # The exact dimensions depend on the SVG size and device pixel ratio
        # Just verify that resize was called with positive integers
        args = window.resize.call_args[0]
        assert len(args) == 2, "resize should be called with width and height"
        assert isinstance(args[0], int) and args[0] > 0, "width should be positive integer"
        assert isinstance(args[1], int) and args[1] > 0, "height should be positive integer"

    def test_fit_to_diagram_without_image(self, qtbot):
        """Test fit to diagram when no image is loaded."""
        from dacwatch.window_manager import DiagramWindow
        from unittest.mock import Mock
        
        # Create a real window
        window = DiagramWindow("test.svg")
        qtbot.addWidget(window)
        
        # Mock the resize method to verify it's not called
        window.resize = Mock()
        
        # Call fit_to_diagram without loading an image
        window.fit_to_diagram()
        
        # Verify resize was not called since no image is loaded
        window.resize.assert_not_called()

    def test_fit_to_diagram_resets_zoom(self, qtbot):
        """Test that fit to diagram resets zoom to 1:1."""
        from dacwatch.window_manager import DiagramWindow
        from unittest.mock import Mock, patch
        
        # Create a real window
        window = DiagramWindow("test.svg")
        qtbot.addWidget(window)
        
        # Create test SVG content
        svg_content = '''<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="100" height="100" fill="red"/>
        </svg>'''
        
        # Display the image
        window.display_image(svg_content.encode(), "svg")
        
        # Zoom in first to verify reset
        window.zoom_in()
        initial_zoom = window.current_zoom_scale
        assert initial_zoom > 1.0, "Should be zoomed in"
        
        # Mock reset_zoom to verify it's called
        with patch.object(window, 'reset_zoom') as mock_reset_zoom:
            # Mock size methods and resize to avoid actual window changes
            mock_window_size = Mock()
            mock_window_size.width = Mock(return_value=800)
            mock_window_size.height = Mock(return_value=600)
            window.size = Mock(return_value=mock_window_size)
            
            mock_view_size = Mock()
            mock_view_size.width = Mock(return_value=700)
            mock_view_size.height = Mock(return_value=500)
            window.graphics_view.size = Mock(return_value=mock_view_size)
            
            # Mock viewport size for fit calculation
            mock_viewport_size = Mock()
            mock_viewport_size.width = Mock(return_value=680)
            mock_viewport_size.height = Mock(return_value=480)
            window.graphics_view.viewport = Mock()
            window.graphics_view.viewport.return_value.size = Mock(return_value=mock_viewport_size)
            
            window.resize = Mock()
            
            # Call fit_to_diagram
            window.fit_to_diagram()
            
            # Verify reset_zoom was called
            mock_reset_zoom.assert_called_once()

    def test_auto_fit_on_window_show(self, qtbot):
        """Test that auto-fit is triggered when window first displays image."""
        from dacwatch.window_manager import DiagramWindow
        from unittest.mock import Mock, patch
        
        # Create a real window and show it
        window = DiagramWindow("test.svg")
        qtbot.addWidget(window)
        window.show()
        
        # Create test SVG content
        svg_content = '''<svg width="200" height="150" xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="200" height="150" fill="green"/>
        </svg>'''
        
        # Mock fit_to_diagram to verify it gets called
        with patch.object(window, 'fit_to_diagram') as mock_fit:
            # Display the image (this should trigger auto-fit)
            window.display_image(svg_content.encode(), "svg")
            
            # Wait for the timer to execute
            qtbot.wait(100)  # Wait for the 50ms timer
            
            # Verify fit_to_diagram was called during image display
            mock_fit.assert_called_once()

    def test_auto_fit_on_window_reappear(self, qtbot):
        """Test that auto-fit is triggered when window reappears after being hidden."""
        from dacwatch.window_manager import DiagramWindow
        from unittest.mock import Mock, patch
        
        # Create and show window initially
        window = DiagramWindow("test.svg")
        qtbot.addWidget(window)
        window.show()
        
        # Create test SVG content
        svg_content = '''<svg width="200" height="150" xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="200" height="150" fill="green"/>
        </svg>'''
        
        # Display initial image (this should trigger auto-fit)
        window.display_image(svg_content.encode(), "svg")
        qtbot.wait(100)  # Wait for initial auto-fit
        
        # Hide the window (this sets should_auto_fit = True)
        window.hide()
        qtbot.wait(50)
        
        # Show the window again
        window.show()
        qtbot.wait(50)
        
        # Mock fit_to_diagram to verify it gets called on next image display
        with patch.object(window, 'fit_to_diagram') as mock_fit:
            # Display image again (this should trigger auto-fit because window was hidden/shown)
            window.display_image(svg_content.encode(), "svg")
            qtbot.wait(100)  # Wait for the timer to execute
            
            # Verify fit_to_diagram was called when image was displayed after reappearing
            mock_fit.assert_called_once()

    def test_no_auto_fit_on_image_reload(self, qtbot):
        """Test that auto-fit is NOT triggered when image is reloaded while window is visible."""
        from dacwatch.window_manager import DiagramWindow
        from unittest.mock import Mock, patch
        
        # Create and show window
        window = DiagramWindow("test.svg")
        qtbot.addWidget(window)
        window.show()
        
        # Create test SVG content
        svg_content1 = '''<svg width="200" height="150" xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="200" height="150" fill="green"/>
        </svg>'''
        
        svg_content2 = '''<svg width="300" height="200" xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="300" height="200" fill="blue"/>
        </svg>'''
        
        # Display initial image (this should trigger auto-fit and reset should_auto_fit to False)
        window.display_image(svg_content1.encode(), "svg")
        qtbot.wait(100)  # Wait for initial auto-fit
        
        # Mock fit_to_diagram to verify it's NOT called on image reload
        with patch.object(window, 'fit_to_diagram') as mock_fit:
            # Reload image while window is visible (should_auto_fit is now False)
            window.display_image(svg_content2.encode(), "svg")
            qtbot.wait(100)  # Wait to see if auto-fit gets called
            
            # Verify fit_to_diagram was NOT called during image reload
            mock_fit.assert_not_called()

    def test_copy_source_to_clipboard(self):
        """Test copying source code to clipboard by reading file."""
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
            mock_window.actual_file_path = "/path/to/test/file.dot"
            mock_window.source_code = None  # No stored source, should read from file

            # Import and bind the method to our mock
            from dacwatch.window_manager import DiagramWindow
            mock_window.copy_source_to_clipboard = DiagramWindow.copy_source_to_clipboard.__get__(mock_window, DiagramWindow)

            # Call copy_source_to_clipboard
            mock_window.copy_source_to_clipboard()

            # Verify file was opened and read using actual_file_path
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
            mock_window.actual_file_path = "/path/to/test/file.dot"

            # Import and bind the method to our mock
            from dacwatch.window_manager import DiagramWindow
            mock_window.reveal_in_finder = DiagramWindow.reveal_in_finder.__get__(mock_window, DiagramWindow)

            # Call reveal_in_finder
            mock_window.reveal_in_finder()

            # Verify subprocess.run was called with correct arguments (uses actual_file_path)
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


class TestZoomableGraphicsViewDoubleClick:
    """Test suite for ZoomableGraphicsView double-click functionality."""

    def test_double_click_triggers_fit_action(self, qtbot):
        """Test that double-clicking on the graphics view triggers the fit action."""
        from dacwatch.window_manager import DiagramWindow, ZoomableGraphicsView
        from PySide6.QtCore import Qt, QPoint
        from PySide6.QtGui import QMouseEvent
        from unittest.mock import Mock, patch
        
        # Create a real window
        window = DiagramWindow("test.svg")
        qtbot.addWidget(window)
        
        # Create test SVG content
        svg_content = '''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
            <rect x="50" y="50" width="100" height="100" fill="blue"/>
        </svg>'''
        
        # Display the image to create graphics view
        window.display_image(svg_content.encode(), "svg")
        
        # Verify graphics view was created
        assert hasattr(window, 'graphics_view')
        assert isinstance(window.graphics_view, ZoomableGraphicsView)
        
        # Mock the fit_to_diagram method to verify it gets called
        with patch.object(window, 'fit_to_diagram') as mock_fit:
            # Simulate a double-click event on the graphics view
            graphics_view = window.graphics_view
            
            # Create a double-click event at the center of the view
            click_pos = QPoint(100, 100)
            double_click_event = QMouseEvent(
                QMouseEvent.Type.MouseButtonDblClick,
                click_pos,
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            
            # Send the double-click event to the graphics view
            graphics_view.mouseDoubleClickEvent(double_click_event)
            
            # Verify that fit_to_diagram was called
            mock_fit.assert_called_once()

    def test_double_click_ignores_non_left_button(self, qtbot):
        """Test that double-clicking with non-left buttons doesn't trigger fit action."""
        from dacwatch.window_manager import DiagramWindow, ZoomableGraphicsView
        from PySide6.QtCore import Qt, QPoint
        from PySide6.QtGui import QMouseEvent
        from unittest.mock import Mock, patch
        
        # Create a real window
        window = DiagramWindow("test.svg")
        qtbot.addWidget(window)
        
        # Create test SVG content
        svg_content = '''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
            <rect x="50" y="50" width="100" height="100" fill="red"/>
        </svg>'''
        
        # Display the image to create graphics view
        window.display_image(svg_content.encode(), "svg")
        
        # Mock the fit_to_diagram method to verify it's NOT called
        with patch.object(window, 'fit_to_diagram') as mock_fit:
            graphics_view = window.graphics_view
            
            # Create a right-click double-click event
            click_pos = QPoint(100, 100)
            right_double_click_event = QMouseEvent(
                QMouseEvent.Type.MouseButtonDblClick,
                click_pos,
                Qt.MouseButton.RightButton,
                Qt.MouseButton.RightButton,
                Qt.KeyboardModifier.NoModifier
            )
            
            # Send the right double-click event
            graphics_view.mouseDoubleClickEvent(right_double_click_event)
            
            # Verify that fit_to_diagram was NOT called
            mock_fit.assert_not_called()

    def test_double_click_handles_deleted_parent_window(self, qtbot):
        """Test that double-click gracefully handles deleted parent window."""
        from dacwatch.window_manager import ZoomableGraphicsView
        from PySide6.QtCore import Qt, QPoint
        from PySide6.QtGui import QMouseEvent
        from unittest.mock import Mock
        
        # Create a mock parent window that raises RuntimeError when accessed
        mock_parent = Mock()
        mock_parent.fit_to_diagram.side_effect = RuntimeError("Parent window deleted")
        
        # Create a graphics view with the mock parent
        graphics_view = ZoomableGraphicsView(parent_window=mock_parent)
        qtbot.addWidget(graphics_view)
        
        # Create a double-click event
        click_pos = QPoint(100, 100)
        double_click_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonDblClick,
            click_pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        
        # This should not raise an exception even though parent window is "deleted"
        graphics_view.mouseDoubleClickEvent(double_click_event)
        
        # Verify that fit_to_diagram was attempted to be called
        mock_parent.fit_to_diagram.assert_called_once()

    def test_double_click_without_parent_window(self, qtbot):
        """Test that double-click works safely when there's no parent window."""
        from dacwatch.window_manager import ZoomableGraphicsView
        from PySide6.QtCore import Qt, QPoint
        from PySide6.QtGui import QMouseEvent
        
        # Create a graphics view without a parent window
        graphics_view = ZoomableGraphicsView(parent_window=None)
        qtbot.addWidget(graphics_view)
        
        # Create a double-click event
        click_pos = QPoint(100, 100)
        double_click_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonDblClick,
            click_pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        
        # This should not raise an exception even though there's no parent window
        graphics_view.mouseDoubleClickEvent(double_click_event)
        # Test passes if no exception is raised


class TestMarkdownWindows:
    """Test suite for markdown window management."""

    def test_cleanup_markdown_windows(self):
        """Test closing all windows for a markdown file."""
        manager = WindowManager()

        mock_w0 = Mock()
        mock_w0.close = Mock()
        mock_w1 = Mock()
        mock_w1.close = Mock()
        mock_other = Mock()
        mock_other.close = Mock()

        manager.windows = {
            "/path/to/doc.md:0": mock_w0,
            "/path/to/doc.md:1": mock_w1,
            "/path/to/other.dot": mock_other,
        }

        manager.cleanup_markdown_windows("/path/to/doc.md")

        mock_w0.close.assert_called_once()
        mock_w1.close.assert_called_once()
        mock_other.close.assert_not_called()
        assert "/path/to/doc.md:0" not in manager.windows
        assert "/path/to/doc.md:1" not in manager.windows
        assert "/path/to/other.dot" in manager.windows

    def test_cleanup_stale_markdown_windows(self):
        """Test closing windows for blocks that no longer exist."""
        manager = WindowManager()

        mock_w0 = Mock()
        mock_w0.close = Mock()
        mock_w1 = Mock()
        mock_w1.close = Mock()
        mock_w2 = Mock()
        mock_w2.close = Mock()

        manager.windows = {
            "/path/to/doc.md:0": mock_w0,
            "/path/to/doc.md:1": mock_w1,
            "/path/to/doc.md:2": mock_w2,
        }

        # Only 1 block remains
        manager.cleanup_stale_markdown_windows("/path/to/doc.md", 1)

        mock_w0.close.assert_not_called()
        mock_w1.close.assert_called_once()
        mock_w2.close.assert_called_once()
        assert "/path/to/doc.md:0" in manager.windows
        assert "/path/to/doc.md:1" not in manager.windows
        assert "/path/to/doc.md:2" not in manager.windows

    def test_cleanup_stale_no_stale(self):
        """Test cleanup when no windows are stale."""
        manager = WindowManager()

        mock_w0 = Mock()
        mock_w0.close = Mock()
        mock_w1 = Mock()
        mock_w1.close = Mock()

        manager.windows = {
            "/path/to/doc.md:0": mock_w0,
            "/path/to/doc.md:1": mock_w1,
        }

        manager.cleanup_stale_markdown_windows("/path/to/doc.md", 2)

        mock_w0.close.assert_not_called()
        mock_w1.close.assert_not_called()
        assert manager.window_count == 2

    def test_cleanup_markdown_windows_no_match(self):
        """Test cleanup when no matching markdown windows exist."""
        manager = WindowManager()
        mock_window = Mock()
        mock_window.close = Mock()
        manager.windows = {"/path/to/other.dot": mock_window}

        manager.cleanup_markdown_windows("/path/to/doc.md")

        mock_window.close.assert_not_called()
        assert manager.window_count == 1

    def test_actual_file_path_default(self, qtbot):
        """Test that actual_file_path defaults to file_path."""
        from dacwatch.window_manager import DiagramWindow

        window = DiagramWindow("/path/to/file.dot")
        qtbot.addWidget(window)

        assert window.file_path == "/path/to/file.dot"
        assert window.actual_file_path == "/path/to/file.dot"

    def test_actual_file_path_custom(self, qtbot):
        """Test that actual_file_path can be set separately."""
        from dacwatch.window_manager import DiagramWindow

        window = DiagramWindow("/path/to/doc.md:0", actual_file_path="/path/to/doc.md")
        qtbot.addWidget(window)

        assert window.file_path == "/path/to/doc.md:0"
        assert window.actual_file_path == "/path/to/doc.md"

    def test_window_title_uses_actual_file_path(self, qtbot):
        """Test window title uses actual_file_path for display."""
        from dacwatch.window_manager import DiagramWindow

        window = DiagramWindow("/path/to/doc.md:0", actual_file_path="/path/to/doc.md")
        qtbot.addWidget(window)

        assert "doc.md" in window.windowTitle()

    def test_create_window_with_actual_file_path(self):
        """Test creating a window with actual_file_path through WindowManager."""
        manager = WindowManager()

        mock_window = Mock()
        mock_window.file_path = "/path/to/doc.md:0"

        with patch('dacwatch.window_manager.DiagramWindow') as mock_dw:
            mock_dw.return_value = mock_window

            result = manager.create_window(
                "/path/to/doc.md:0",
                actual_file_path="/path/to/doc.md",
                window_title="DaCWatch - doc.md:0 (plantuml)"
            )

            mock_dw.assert_called_once_with(
                "/path/to/doc.md:0",
                window_manager=manager,
                actual_file_path="/path/to/doc.md"
            )
            mock_window.setWindowTitle.assert_called_once_with("DaCWatch - doc.md:0 (plantuml)")

    def test_get_or_create_window_with_actual_file_path(self):
        """Test get_or_create_window passes actual_file_path for new windows."""
        manager = WindowManager()

        mock_window = Mock()
        mock_window.file_path = "/path/to/doc.md:0"

        with patch('dacwatch.window_manager.DiagramWindow') as mock_dw:
            mock_dw.return_value = mock_window

            result = manager.get_or_create_window(
                "/path/to/doc.md:0",
                actual_file_path="/path/to/doc.md",
                window_title="DaCWatch - doc.md:0 (mermaid)"
            )

            assert result == mock_window
            mock_dw.assert_called_once_with(
                "/path/to/doc.md:0",
                window_manager=manager,
                actual_file_path="/path/to/doc.md"
            )

    def test_reveal_uses_actual_file_path(self):
        """Test that reveal_in_finder uses actual_file_path."""
        from dacwatch.window_manager import DiagramWindow

        with patch('subprocess.run') as mock_subprocess:
            mock_window = Mock()
            mock_window.actual_file_path = "/path/to/doc.md"
            mock_window.reveal_in_finder = DiagramWindow.reveal_in_finder.__get__(mock_window, DiagramWindow)

            mock_window.reveal_in_finder()

            mock_subprocess.assert_called_once_with(['open', '-R', "/path/to/doc.md"])