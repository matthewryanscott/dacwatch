import asyncio
from typing import Optional
from queue import Queue
import threading
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from .config import Config
from .file_watcher import FileWatcher
from .window_manager import WindowManager
from .kroki_client import KrokiClient


class DaCWatchApp:
    """Main application class for DaCWatch."""

    def __init__(self, config: Config):
        self.config = config
        self.is_running = False
        self.file_watcher: Optional[FileWatcher] = None
        self.window_manager: Optional[WindowManager] = None
        self.kroki_client: Optional[KrokiClient] = None
        self.qt_app: Optional[QApplication] = None
        self.event_queue = Queue()
        self.file_watcher_thread: Optional[threading.Thread] = None

    async def start(self):
        """Start the application."""
        self.is_running = True
        print(f"DaCWatch starting - watching directory: {self.config.directory}")
        print(f"Using Kroki service: {self.config.kroki_base}")

        # Initialize Qt application with high-DPI support
        if QApplication.instance() is None:
            # Enable high-DPI support before creating QApplication
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
            self.qt_app = QApplication([])

        # Initialize the window manager
        self.window_manager = WindowManager()

        # Initialize the Kroki client
        self.kroki_client = KrokiClient(self.config.kroki_base)

        # Setup application-level keyboard shortcuts
        self._setup_app_shortcuts()

        # Start the file watcher
        self.file_watcher = FileWatcher(self.config, self._handle_file_event)
        await self.file_watcher.start()

    def _setup_app_shortcuts(self):
        """Setup application-level keyboard shortcuts."""
        from PySide6.QtGui import QShortcut, QKeySequence
        from PySide6.QtCore import Qt

        # Get the QApplication instance
        app = QApplication.instance()
        if not app:
            return

        # Cycle windows forward (Cmd+Shift+] / Cmd+})
        cycle_forward = QShortcut(QKeySequence("Ctrl+Shift+]"), app)
        cycle_forward.setContext(Qt.ShortcutContext.ApplicationShortcut)
        cycle_forward.activated.connect(lambda: self._cycle_windows(False))

        # Cycle windows backward (Cmd+Shift+[ / Cmd+{)
        cycle_backward = QShortcut(QKeySequence("Ctrl+Shift+["), app)
        cycle_backward.setContext(Qt.ShortcutContext.ApplicationShortcut)
        cycle_backward.activated.connect(lambda: self._cycle_windows(True))

    def _cycle_windows(self, backward=False):
        """Cycle through windows."""
        if self.window_manager:
            self.window_manager.cycle_to_next_window(backward=backward)

    async def stop(self):
        """Stop the application."""
        self.is_running = False

        # Stop the file watcher
        if self.file_watcher:
            await self.file_watcher.stop()

        print("DaCWatch stopped")

    async def _handle_file_event(self, event_type: str, file_path: str):
        """Handle file events by creating/updating windows and rendering diagrams."""
        if not self.window_manager or not self.kroki_client:
            return

        if event_type in ['created', 'modified']:
            # Create or get window for the file
            window = self.window_manager.get_or_create_window(file_path)
            if window:
                window.show()  # Make sure the window is visible

                # Set up format toggle callback - use a safer approach that doesn't capture window directly
                def create_format_callback(fp, wm):
                    def format_callback(new_format):
                        # Get the current window reference (in case it was recreated)
                        current_window = wm.get_window_for_file(fp)
                        if current_window:
                            asyncio.create_task(
                                self._render_and_display_diagram(fp, current_window, new_format)
                            )
                    return format_callback
                
                window.format_toggle_callback = create_format_callback(file_path, self.window_manager)

                # Render and display the diagram
                try:
                    await self._render_and_display_diagram(file_path, window)
                except Exception as e:
                    print(f"Error rendering diagram for {file_path}: {e}")

        elif event_type == 'deleted':
            # Clean up window for deleted file
            self.window_manager.cleanup_deleted_file(file_path)

    async def _render_and_display_diagram(self, file_path: str, window, format: str = "svg"):
        """Render a diagram and display it in the window."""
        if not self.kroki_client:
            print(f"Kroki client not available")
            return
            
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # Determine diagram type
            diagram_type = self.kroki_client.get_diagram_type(file_path)
            if not diagram_type:
                print(f"Unsupported file type for {file_path}")
                return

            # Render the diagram with specified format
            image_data = await self.kroki_client.render_diagram(source_code, diagram_type, format)

            # Store the source and image data on the window for toolbar actions
            window.image_data = image_data
            window.source_code = source_code
            window.current_format = format

            # Display the image
            window.display_image(image_data, format)

        except FileNotFoundError:
            print(f"File not found: {file_path}")
            window.display_error("File not found", f"Could not read file: {file_path}", f"File not found: {file_path}")
        except Exception as e:
            print(f"Error rendering diagram: {e}")
            # Parse error message for better user display
            error_msg = str(e)
            error_details = ""
            
            # Extract detailed error information if available
            try:
                if hasattr(e, 'message'):
                    error_details = str(getattr(e, 'message', ''))
                elif hasattr(e, 'args') and len(e.args) > 0:
                    error_details = str(e.args[0])
                else:
                    error_details = error_msg
            except:
                error_details = error_msg
            
            # Extract raw error response body if available (for textarea)
            error_body = ""
            try:
                if hasattr(e, 'body'):
                    error_body = str(getattr(e, 'body', ''))
                elif "Error details:" in error_details:
                    # Extract just the response part
                    parts = error_details.split("Error details:")
                    if len(parts) > 1:
                        error_body = parts[1].strip()
                else:
                    error_body = error_details
            except:
                error_body = error_msg
            
            if "400" in error_msg or "Bad Request" in error_msg:
                # Extract syntax error details from Kroki response
                main_msg = "Diagram syntax error"
                details = "The diagram contains invalid syntax. Please check your diagram code for errors."
                window.display_error(main_msg, details, error_body)
                
            elif "500" in error_msg:
                window.display_error("Server error", 
                    "The Kroki service encountered an error. Please try again later.", error_body)
                    
            elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                kroki_url = self.config.kroki_base if hasattr(self.config, 'kroki_base') else "Kroki service"
                window.display_error("Network error", 
                    f"Could not connect to Kroki service: {kroki_url}", error_body)
            else:
                window.display_error("Rendering error", "Unexpected error occurred.", error_body)



    async def run(self):
        """Run the main application loop."""
        await self.start()
        
        # Keep the async loop running indefinitely
        # The qasync integration will handle Qt events automatically
        try:
            while self.is_running:
                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            print("Received interrupt signal")
        except asyncio.CancelledError:
            print("Application cancelled")
        finally:
            await self.stop()