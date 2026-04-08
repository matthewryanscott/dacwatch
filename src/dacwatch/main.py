import asyncio
from pathlib import Path

import aiohttp
import typer

from dacwatch.app import DaCWatchApp
from dacwatch.config import Config
from dacwatch.kroki_client import KrokiClient, KrokiError

app = typer.Typer(name="dacwatch", help="DaCWatch - Diagram as Code File Watcher")


def _format_kroki_startup_error(kroki_base: str, error: Exception) -> str:
    """Return a friendly startup error for Kroki connectivity problems."""
    lines = [
        f"Could not reach a working Kroki service at {kroki_base}.",
        "DaCWatch checks Kroki at startup so connection problems fail fast before the GUI starts.",
    ]

    if isinstance(error, KrokiError):
        details = f"Kroki responded with HTTP {error.status} {error.reason}."
        if error.body:
            snippet = error.body.strip().splitlines()[0][:200]
            details += f" Response: {snippet}"
        lines.append(details)
    else:
        lines.append(f"Connection error: {error}")

    lines.extend([
        "",
        "Try one of these:",
        "- Start the bundled local Kroki stack: cd kroki-self-hosted && docker compose up -d",
        "- Or use the public service explicitly: dacwatch --kroki-base=https://kroki.io <dir>",
        "- Verify that the Kroki base URL is correct and reachable from this machine",
    ])
    return "\n".join(lines)


async def validate_kroki_connection(kroki_base: str):
    """Fail fast with a helpful message if Kroki is unreachable at startup."""
    client = KrokiClient(kroki_base)
    try:
        await client.check_connection()
    except (KrokiError, aiohttp.ClientError, TimeoutError, OSError) as exc:
        raise RuntimeError(_format_kroki_startup_error(kroki_base, exc)) from exc


@app.command(name="dacwatch")
def main(
    directories: list[Path] = typer.Argument(..., help="Directories to watch for diagram files"),
    kroki_base: str = typer.Option("http://localhost:48000", help="Kroki service base URL"),
    dry_run: bool = typer.Option(False, help="Dry run - validate config and exit"),
):
    """
    Watch directories for diagram files and render them using Kroki service.
    """
    # Create configuration from CLI arguments
    config = Config.from_cli_args(directories, kroki_base)

    for d in config.directories:
        typer.echo(f"Watching directory: {d}")
    typer.echo(f"Using Kroki service: {config.kroki_base}")

    if dry_run:
        typer.echo("Dry run completed successfully")
        return

    try:
        asyncio.run(validate_kroki_connection(config.kroki_base))
    except RuntimeError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

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
