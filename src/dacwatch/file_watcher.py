import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .config import Config
from .file_type import is_supported_file


class AsyncEventHandler(FileSystemEventHandler):
    """Async event handler for file system events."""

    def __init__(self, file_watcher, loop):
        self.file_watcher = file_watcher
        self.loop = loop

    def _schedule_async_task(self, event_data):
        """Safely schedule an async task."""
        try:
            if self.loop and not self.loop.is_closed():
                # Try to schedule the task on the original loop
                self.loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(self.file_watcher.handle_file_event(event_data))
                )
            else:
                # Fallback: try to get the running loop and schedule there
                try:
                    current_loop = asyncio.get_running_loop()
                    current_loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(self.file_watcher.handle_file_event(event_data))
                    )
                except RuntimeError:
                    # No running loop, create a new one in a thread
                    import threading
                    
                    def run_in_thread():
                        try:
                            asyncio.run(self.file_watcher.handle_file_event(event_data))
                        except Exception as e:
                            print(f"Error processing file event: {e}")
                    
                    thread = threading.Thread(target=run_in_thread, daemon=True)
                    thread.start()
        except Exception as e:
            print(f"Error scheduling async task: {e}")

    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self._schedule_async_task({
                'event_type': 'created',
                'src_path': event.src_path,
                'is_directory': event.is_directory
            })

    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            self._schedule_async_task({
                'event_type': 'modified',
                'src_path': event.src_path,
                'is_directory': event.is_directory
            })

    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory:
            self._schedule_async_task({
                'event_type': 'deleted',
                'src_path': event.src_path,
                'is_directory': event.is_directory
            })

    def on_moved(self, event):
        """Handle file move/rename events (e.g., atomic writes via temp files)."""
        if not event.is_directory:
            # Treat the destination as a created/modified file
            self._schedule_async_task({
                'event_type': 'created',
                'src_path': event.dest_path,
                'is_directory': event.is_directory
            })


class FileWatcher:
    """Async file watcher using watchdog with event debouncing."""

    def __init__(self, config: Config, event_callback=None):
        self.config = config
        self.event_callback = event_callback
        self.is_watching = False
        self.observer = None
        self.event_handler = None

        # Event queue for debouncing
        self.event_queue = asyncio.Queue()
        self.pending_events: Dict[str, Set[str]] = {}  # file_path -> set of event types
        self.debounce_delay = 1.0  # seconds
        self.processing_task = None
        self.debounce_task: Optional[asyncio.Task] = None  # Task for debounce timer

    async def start(self):
        """Start watching the directory."""
        if self.is_watching:
            return

        self.is_watching = True
        loop = asyncio.get_running_loop()
        self.event_handler = AsyncEventHandler(self, loop)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, str(self.config.directory), recursive=True)
        self.observer.start()

        # Start the event processing task
        self.processing_task = asyncio.create_task(self._process_events())



    async def stop(self):
        """Stop watching the directory."""
        if not self.is_watching:
            return

        self.is_watching = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None

        # Stop the event processing task
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass

        # Stop any pending debounce task
        if self.debounce_task and not self.debounce_task.done():
            self.debounce_task.cancel()
            try:
                await self.debounce_task
            except asyncio.CancelledError:
                pass

    async def handle_file_event(self, event: Dict[str, Any]):
        """Handle a file system event by queuing it for processing."""
        file_path = Path(event['src_path'])
        file_path_str = str(file_path)

        # Only process supported file types
        if not is_supported_file(file_path):
            return

        # Add to queue for debounced processing
        await self.event_queue.put(event)

    async def _process_events(self):
        """Process events from the queue with debouncing."""
        while self.is_watching:
            try:
                # Wait for an event
                event = await self.event_queue.get()
                file_path = event['src_path']
                event_type = event['event_type']

                # Update pending events (accumulate event types for each file)
                if file_path not in self.pending_events:
                    self.pending_events[file_path] = set()
                self.pending_events[file_path].add(event_type)

                # Schedule processing after debounce delay
                await self._schedule_debounce_processing()

            except asyncio.CancelledError:
                break

    async def _schedule_debounce_processing(self):
        """Schedule event processing after debounce delay."""
        # Cancel any existing debounce task
        if self.debounce_task and not self.debounce_task.done():
            self.debounce_task.cancel()

        # Schedule new debounce task
        self.debounce_task = asyncio.create_task(self._debounce_and_process())

    async def _debounce_and_process(self):
        """Process pending events after debounce delay has passed."""
        try:
            # Wait for debounce delay
            await asyncio.sleep(self.debounce_delay)
        except asyncio.CancelledError:
            # Debounce was cancelled due to new events, don't process yet
            return

        if not self.pending_events:
            return

        # Process all pending events
        for file_path, event_types in self.pending_events.items():
            flattened_event = self._flatten_events(event_types, file_path)
            if flattened_event:
                await self._process_single_event(flattened_event, file_path)

        # Clear pending events
        self.pending_events.clear()

    def _flatten_events(self, event_types: Set[str], file_path: str) -> Optional[str]:
        """
        Flatten multiple event types into a single meaningful event.

        Uses file existence to determine actual state rather than relying on event order.
        """
        file_exists = Path(file_path).exists()

        # If we have created or modified events and file exists, prioritize that
        if 'created' in event_types:
            if file_exists:
                return 'created'
            else:
                # Created then deleted - file is gone
                return 'deleted'
        elif 'modified' in event_types:
            if file_exists:
                return 'modified'
            else:
                # Modified then deleted - file is gone
                return 'deleted'
        elif 'deleted' in event_types:
            # Only deletion events
            return 'deleted'
        else:
            # No valid events
            return None

    async def _process_single_event(self, event_type: str, file_path: str):
        """Process a single file event."""
        file_path_obj = Path(file_path)

        print(f"Processed file event: {event_type} - {file_path_obj}")

        # Call the event callback if provided
        if self.event_callback:
            await self.event_callback(event_type, file_path)