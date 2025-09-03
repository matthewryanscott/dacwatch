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

    # Create and run the application
    dac_app = DaCWatchApp(config)

    # Run the async application
    try:
        asyncio.run(dac_app.run())
    except KeyboardInterrupt:
        typer.echo("Received interrupt signal, shutting down...")
        # The app will handle cleanup in its stop method


if __name__ == "__main__":
    app()
