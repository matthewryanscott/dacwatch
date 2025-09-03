import asyncio
from typing import Optional
from config import Config


class DaCWatchApp:
    """Main application class for DaCWatch."""

    def __init__(self, config: Config):
        self.config = config
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the application."""
        self.is_running = True
        print(f"DaCWatch starting - watching directory: {self.config.directory}")
        print(f"Using Kroki service: {self.config.kroki_base}")

    async def stop(self):
        """Stop the application."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("DaCWatch stopped")

    async def run(self):
        """Run the main application loop."""
        await self.start()

        try:
            # Main event loop - for now just keep running
            while self.is_running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()