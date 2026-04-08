import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from typer.testing import CliRunner

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dacwatch.kroki_client import KrokiError
from dacwatch.main import app, configure_logging, validate_kroki_connection


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_help(runner):
    """Test that CLI shows help message."""
    result = runner.invoke(app, ["--help"], color=False, terminal_width=120)
    assert result.exit_code == 0
    assert "dacwatch" in result.output
    assert "Usage:" in result.output
    assert "directories" in result.output.lower()
    assert "--help" in result.output
    assert "Kroki service" in result.output


def test_configure_logging_defaults_to_warning():
    """Logging should default to warning-level output."""
    with patch("dacwatch.main.logging.basicConfig") as mock_basic_config:
        configure_logging()

    mock_basic_config.assert_called_once()
    assert mock_basic_config.call_args.kwargs["level"] == 30
    assert mock_basic_config.call_args.kwargs["force"] is True


def test_configure_logging_verbose_sets_info_level():
    """Verbose mode should enable info logs."""
    with patch("dacwatch.main.logging.basicConfig") as mock_basic_config:
        configure_logging(verbose=True)

    assert mock_basic_config.call_args.kwargs["level"] == 20


def test_configure_logging_debug_sets_debug_level():
    """Debug mode should enable debug logs."""
    with patch("dacwatch.main.logging.basicConfig") as mock_basic_config:
        configure_logging(debug=True)

    assert mock_basic_config.call_args.kwargs["level"] == 10


def test_cli_with_directory(runner, tmp_path):
    """Test CLI with directory argument."""
    test_dir = tmp_path / "test_diagrams"
    test_dir.mkdir()

    result = runner.invoke(app, [str(test_dir), "--dry-run"])
    # For now, this should succeed since we have basic CLI structure
    assert result.exit_code == 0
    assert f"Watching directory: {test_dir}" in result.output
    assert "Dry run completed successfully" in result.output


def test_cli_with_kroki_base(runner, tmp_path):
    """Test CLI with kroki-base option."""
    test_dir = tmp_path / "test_diagrams"
    test_dir.mkdir()

    kroki_url = "https://custom.kroki.io"
    result = runner.invoke(app, ["--kroki-base", kroki_url, str(test_dir), "--dry-run"])
    assert result.exit_code == 0
    assert f"Using Kroki service: {kroki_url}" in result.output
    assert "Dry run completed successfully" in result.output


def test_cli_missing_directory(runner):
    """Test CLI fails when directory is not provided."""
    result = runner.invoke(app)
    assert result.exit_code != 0
    assert "Missing argument" in result.output


def test_cli_invalid_kroki_base(runner, tmp_path):
    """Test CLI with invalid kroki-base URL."""
    test_dir = tmp_path / "test_diagrams"
    test_dir.mkdir()

    result = runner.invoke(app, ["--kroki-base", "invalid-url", str(test_dir), "--dry-run"])
    # Should fail with invalid URL
    assert result.exit_code == 1
    assert "Invalid kroki_base URL" in str(result.exception)


@pytest.mark.asyncio
async def test_validate_kroki_connection_success():
    """Startup validation should pass when Kroki is reachable."""
    with patch("dacwatch.main.KrokiClient.check_connection", new=AsyncMock()) as mock_check:
        await validate_kroki_connection("https://kroki.io")

    mock_check.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_kroki_connection_surfaces_helpful_network_error():
    """Startup validation should explain how to recover from connection failures."""
    with patch(
        "dacwatch.main.KrokiClient.check_connection",
        new=AsyncMock(side_effect=aiohttp.ClientError("connection refused")),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            await validate_kroki_connection("http://localhost:48000")

    message = str(exc_info.value)
    assert "Could not reach a working Kroki service" in message
    assert "docker compose up -d" in message
    assert "https://kroki.io" in message


@pytest.mark.asyncio
async def test_validate_kroki_connection_surfaces_http_error_details():
    """Startup validation should include Kroki HTTP error details."""
    with patch(
        "dacwatch.main.KrokiClient.check_connection",
        new=AsyncMock(side_effect=KrokiError(502, "Bad Gateway", "upstream unavailable")),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            await validate_kroki_connection("https://broken.kroki.example")

    message = str(exc_info.value)
    assert "HTTP 502 Bad Gateway" in message
    assert "upstream unavailable" in message