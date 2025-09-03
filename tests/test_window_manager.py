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