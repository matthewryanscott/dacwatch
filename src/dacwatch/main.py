import asyncio
import typer
from pathlib import Path
from dacwatch.config import Config
from dacwatch.app import DaCWatchApp

app = typer.Typer(name="dacwatch", help="DaCWatch - Diagram as Code File Watcher")


@app.command(name="dacwatch")
def main(
    directory: Path = typer.Argument(..., help="Directory to watch for diagram files"),
    kroki_base: str = typer.Option("http://localhost:48000", help="Kroki service base URL"),
    dry_run: bool = typer.Option(False, help="Dry run - validate config and exit"),
):
    """
    Watch a directory for diagram files and render them using Kroki service.
    """
    # Create configuration from CLI arguments
    config = Config.from_cli_args(directory, kroki_base)

    typer.echo(f"Watching directory: {config.directory}")
    typer.echo(f"Using Kroki service: {config.kroki_base}")

    if dry_run:
        typer.echo("Dry run completed successfully")
        return

    # Create the application
    dac_app = DaCWatchApp(config)

    # Use qasync for proper asyncio-Qt integration
    try:
        import qasync
    except ImportError:
        typer.echo("Error: qasync is required but not installed. Please install it with: uv add qasync")
        return

    import signal
    import sys
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer

    # Create Qt application in main thread
    if QApplication.instance() is None:
        qt_app = QApplication([])
    else:
        qt_app = QApplication.instance()

    if not qt_app:
        typer.echo("Error: Could not create Qt application")
        return

    # Configure Qt to NOT quit when the last window is closed
    # We want to keep watching for files even when no windows are open
    if hasattr(qt_app, 'setQuitOnLastWindowClosed'):
        qt_app.setQuitOnLastWindowClosed(False)  # type: ignore

    # Set up signal handler for graceful shutdown
    def signal_handler(signum, frame):
        print("\nReceived interrupt signal, shutting down...")
        # Schedule cleanup on the event loop instead of exiting immediately
        loop.create_task(shutdown())

    async def shutdown():
        """Async shutdown handler to cleanup properly."""
        await dac_app.stop()
        qt_app.quit()

    signal.signal(signal.SIGINT, signal_handler)

    # Install a timer to allow Python to process signals
    # Qt's event loop blocks signal handling, so we need to wake it up periodically
    signal_timer = QTimer()
    signal_timer.timeout.connect(lambda: None)  # Do nothing, just wake up the event loop
    signal_timer.start(250)  # Check every 250ms

    # Create the asyncio event loop using qasync
    loop = qasync.QEventLoop(qt_app)
    asyncio.set_event_loop(loop)

    # Store Qt app reference in the DaCWatchApp for later use
    dac_app.qt_app = qt_app  # type: ignore

    try:
        print("DaCWatch starting...")
        print("DaCWatch is now running. Close the windows or press Ctrl+C to stop.")

        # Start the application using the qasync loop
        loop.create_task(dac_app.start())

        # Run the Qt application event loop through qasync
        # This will block until Qt app is closed
        loop.run_forever()

    except KeyboardInterrupt:
        typer.echo("Received interrupt signal, shutting down...")
    finally:
        # Clean up - make sure all tasks are complete
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # Wait for all tasks to be cancelled
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        loop.close()


if __name__ == "__main__":
    app()
