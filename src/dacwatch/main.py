import asyncio
import logging
import subprocess
import sys
from pathlib import Path

import aiohttp
import typer

from dacwatch.app import DaCWatchApp
from dacwatch.config import Config
from dacwatch.ipc import (
    SERVER_LOG_PATH,
    DACWATCH_DIR,
    try_send_to_running_instance,
    wait_for_socket,
)
from dacwatch.kroki_client import KrokiClient, KrokiError

app = typer.Typer(name="dacwatch", help="DaCWatch - Diagram as Code File Watcher")
logger = logging.getLogger(__name__)


def configure_logging(*, verbose: bool = False, debug: bool = False) -> None:
    """Configure application logging for CLI use."""
    level = logging.WARNING
    if verbose:
        level = logging.INFO
    if debug:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        force=True,
    )


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
    paths: list[Path] = typer.Argument(None, help="Directories or files to watch for diagrams"),
    kroki_base: str = typer.Option("http://localhost:48000", help="Kroki service base URL"),
    dry_run: bool = typer.Option(False, help="Dry run - validate config and exit"),
    verbose: bool = typer.Option(False, "--verbose", help="Show informational logs"),
    debug: bool = typer.Option(False, "--debug", help="Show debug logs"),
    serve: bool = typer.Option(
        False, "--serve", hidden=True,
        help="Internal: run as the singleton server (used by the launcher).",
    ),
):
    """
    Watch directories and files for diagram-as-code and render them via Kroki.

    The first invocation launches the singleton DaCWatch app; later invocations
    hand their paths to that running instance and exit. When an instance is
    already running, --kroki-base is ignored (the server keeps its own).
    """
    configure_logging(verbose=verbose, debug=debug)

    # Create configuration from CLI arguments (resolves + validates paths).
    # The server may run with no paths (e.g. launched from the .app bundle);
    # the client requires at least one.
    config = Config.from_cli_args(paths or [], kroki_base)

    for d in config.directories:
        typer.echo(f"Watching directory: {d}")
    for f in config.files:
        typer.echo(f"Watching file: {f}")
    typer.echo(f"Using Kroki service: {config.kroki_base}")

    if dry_run:
        typer.echo("Dry run completed successfully")
        return

    if serve:
        _run_server(config)
        return

    resolved = [str(p) for p in (config.directories + config.files)]
    if not resolved:
        typer.echo("Error: provide at least one directory or file to watch.")
        raise typer.Exit(code=2)

    # Hand off to an already-running instance, if any.
    if try_send_to_running_instance(resolved):
        typer.echo(f"Sent {len(resolved)} path(s) to the running DaCWatch instance.")
        raise typer.Exit(0)

    # No instance running. Validate Kroki in the foreground so connection
    # problems fail fast (the launched server can't report errors to us here).
    try:
        asyncio.run(validate_kroki_connection(config.kroki_base))
    except RuntimeError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

    _launch_server(resolved, config.kroki_base)


def find_app_bundle() -> Path | None:
    """Locate DaCWatch.app, checking paths in priority order."""
    # 1. Relative to the source tree: <project>/dist/DaCWatch.app
    project_root = Path(__file__).resolve().parent.parent.parent
    candidates = [
        project_root / "dist" / "DaCWatch.app",
        Path.home() / "Applications" / "DaCWatch.app",
        Path("/Applications/DaCWatch.app"),
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _launch_server(resolved_paths: list[str], kroki_base: str) -> None:
    """Launch the singleton server, then deliver paths once it is ready.

    Prefers the DaCWatch.app bundle (proper macOS app: menu-bar name, Dock
    icon, foreground activation). Falls back to a detached python process when
    the bundle has not been built.
    """
    DACWATCH_DIR.mkdir(parents=True, exist_ok=True)
    bundle = find_app_bundle()

    if bundle is not None:
        # `open --args` forwards args to the app's executable (our launcher,
        # which already passes --serve). The bundle starts empty; paths are
        # delivered over IPC below.
        subprocess.run(["open", str(bundle), "--args", "--kroki-base", kroki_base])
    else:
        log_file = open(SERVER_LOG_PATH, "w")
        subprocess.Popen(
            [sys.executable, "-m", "dacwatch.main", "--serve",
             "--kroki-base", kroki_base, *resolved_paths],
            start_new_session=True,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )

    if not wait_for_socket(timeout=15.0):
        typer.echo("Error: DaCWatch did not start within 15s.")
        if bundle is None:
            try:
                tail = SERVER_LOG_PATH.read_text().strip().splitlines()[-20:]
                if tail:
                    typer.echo("--- server.log (tail) ---")
                    typer.echo("\n".join(tail))
            except OSError:
                pass
        raise typer.Exit(code=1)

    # Deliver the initial paths over IPC. The bundle started empty; the python
    # fallback already has them via argv, so a resend is harmless (idempotent).
    try_send_to_running_instance(resolved_paths)
    typer.echo("DaCWatch started.")
    raise typer.Exit(0)


def _run_server(config: Config) -> None:
    """Run the singleton server: the qasync/Qt event loop that owns the socket."""
    # Create the application
    dac_app = DaCWatchApp(config)

    # Use qasync for proper asyncio-Qt integration
    try:
        import qasync
    except ImportError:
        typer.echo("Error: qasync is required but not installed. Please install it with: uv add qasync")
        return

    import signal
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

    # App identity: name shown in the menu bar (the .app bundle's CFBundleName
    # is authoritative on macOS; this also covers the python-fallback launch and
    # non-macOS) and the window/Dock icon.
    from PySide6.QtGui import QIcon
    qt_app.setApplicationName("DaCWatch")
    qt_app.setApplicationDisplayName("DaCWatch")
    icon_path = Path(__file__).resolve().parent.parent.parent / "resources" / "icon.png"
    if icon_path.exists():
        qt_app.setWindowIcon(QIcon(str(icon_path)))

    # Configure Qt to NOT quit when the last window is closed
    # We want to keep watching for files even when no windows are open
    if hasattr(qt_app, 'setQuitOnLastWindowClosed'):
        qt_app.setQuitOnLastWindowClosed(False)  # type: ignore

    # Set up signal handler for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received interrupt signal, shutting down")
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
        logger.info("DaCWatch starting")
        logger.info("DaCWatch is now running. Close the windows or press Ctrl+C to stop.")

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
