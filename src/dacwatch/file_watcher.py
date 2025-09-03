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

    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self.loop.create_task(self.file_watcher.handle_file_event({
                'event_type': 'created',
                'src_path': event.src_path,
                'is_directory': event.is_directory
            }))

    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            self.loop.create_task(self.file_watcher.handle_file_event({
                'event_type': 'modified',
                'src_path': event.src_path,
                'is_directory': event.is_directory
            }))

    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory:
            self.loop.create_task(self.file_watcher.handle_file_event({
                'event_type': 'deleted',
                'src_path': event.src_path,
                'is_directory': event.is_directory
            }))


class FileWatcher:
    """Async file watcher using watchdog with event debouncing."""

    def __init__(self, config: Config):
        self.config = config
        self.is_watching = False
        self.observer = None
        self.event_handler = None

        # Event queue for debouncing
        self.event_queue = asyncio.Queue()
        self.pending_events: Dict[str, Dict[str, Any]] = {}
        self.debounce_delay = 0.5  # seconds
        self.processing_task = None

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

    async def handle_file_event(self, event: Dict[str, Any]):
        """Handle a file system event by queuing it for processing."""
        file_path = Path(event['src_path'])

        # Only process supported file types
        if not is_supported_file(file_path):
            return

        # Add to queue for debounced processing
        await self.event_queue.put(event)

    async def _process_events(self):
        """Process events from the queue with debouncing."""
        while self.is_watching:
            try:
                # Wait for an event or timeout
                event = await asyncio.wait_for(self.event_queue.get(), timeout=0.1)
                file_path = event['src_path']

                # Update pending events (debounce by overwriting with latest event)
                self.pending_events[file_path] = event

                # Process pending events after debounce delay
                await self._debounce_and_process()

            except asyncio.TimeoutError:
                # No events in queue, process any pending events
                if self.pending_events:
                    await self._debounce_and_process()
            except asyncio.CancelledError:
                break

    async def _debounce_and_process(self):
        """Process pending events after debounce delay."""
        if not self.pending_events:
            return

        # Wait for debounce delay
        await asyncio.sleep(self.debounce_delay)

        # Process all pending events
        for file_path, event in self.pending_events.items():
            await self._process_single_event(event)

        # Clear pending events
        self.pending_events.clear()

    async def _process_single_event(self, event: Dict[str, Any]):
        """Process a single file event."""
        file_path = Path(event['src_path'])

        # For now, just print the event
        print(f"Processed file event: {event['event_type']} - {file_path}")

        # TODO: Process the event (e.g., trigger diagram rendering)