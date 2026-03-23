import pytest
from typer.testing import CliRunner
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dacwatch.main import app


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_help(runner):
    """Test that CLI shows help message."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "dacwatch" in result.output
    assert "--kroki-base" in result.output
    assert "directories" in result.output.lower()
    assert "--help" in result.output
    assert "Kroki service" in result.output


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