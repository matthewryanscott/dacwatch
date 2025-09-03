import asyncio
import typer
from pathlib import Path
from .config import Config
from .app import DaCWatchApp

app = typer.Typer(name="dacwatch", help="DaCWatch - Diagram as Code File Watcher")


@app.command(name="dacwatch")
def main(
    directory: Path = typer.Argument(..., help="Directory to watch for diagram files"),
    kroki_base: str = typer.Option("https://kroki.io", help="Kroki service base URL"),
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
        qt_app.quit()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)

    # Create the asyncio event loop using qasync
    loop = qasync.QEventLoop(qt_app)
    asyncio.set_event_loop(loop)

    # Store Qt app reference in the DaCWatchApp for later use
    dac_app.qt_app = qt_app  # type: ignore

    try:
        print("DaCWatch starting...")
        print("DaCWatch is now running. Close the windows or press Ctrl+C to stop.")
        
        # Start the application without blocking
        asyncio.ensure_future(dac_app.start())
        
        # Run the Qt application event loop through qasync
        # This will block until Qt app is closed
        loop.run_forever()
        
    except KeyboardInterrupt:
        typer.echo("Received interrupt signal, shutting down...")
        qt_app.quit()
    finally:
        # Clean up
        asyncio.ensure_future(dac_app.stop())
        loop.close()


if __name__ == "__main__":
    app()
