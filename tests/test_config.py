import pytest
from pathlib import Path
import sys

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dacwatch.config import Config


def test_config_creation(tmp_path):
    """Test basic config creation."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    kroki_base = "https://kroki.io"

    config = Config(directories=[directory], kroki_base=kroki_base)

    assert config.directories == [directory]
    assert config.kroki_base == kroki_base


def test_config_default_kroki_base(tmp_path):
    """Test config with default kroki base."""
    directory = tmp_path / "test_dir"
    directory.mkdir()

    config = Config(directories=[directory])

    assert config.directories == [directory]
    assert config.kroki_base == "http://localhost:48000"


def test_config_validation_directory_exists():
    """Test config validates directory exists."""
    # This test assumes we want to validate the directory exists
    # If not, we can remove this test
    pass


def test_config_validation_kroki_base_url(tmp_path):
    """Test config validates kroki base is a valid URL."""
    directory = tmp_path / "test_dir"
    directory.mkdir()

    # Valid URL
    config = Config(directories=[directory], kroki_base="https://custom.kroki.io")
    assert config.kroki_base == "https://custom.kroki.io"

    # Invalid URL should raise ValueError
    with pytest.raises(ValueError):
        Config(directories=[directory], kroki_base="not-a-url")


def test_config_from_cli_args(tmp_path):
    """Test creating config from CLI arguments."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    kroki_base = "https://kroki.io"

    config = Config.from_cli_args([directory], kroki_base)

    assert config.directories == [directory]
    assert config.kroki_base == kroki_base


def test_config_accepts_file(tmp_path):
    """A supported diagram file is accepted and classified as a file."""
    diagram = tmp_path / "graph.dot"
    diagram.write_text("digraph { a -> b }")

    config = Config.from_cli_args([diagram])

    assert config.directories == []
    assert config.files == [diagram.resolve()]


def test_config_mixes_dirs_and_files(tmp_path):
    """Directories and files can be passed together."""
    directory = tmp_path / "dir"
    directory.mkdir()
    diagram = tmp_path / "graph.mermaid"
    diagram.write_text("graph TD; A-->B")

    config = Config.from_cli_args([directory, diagram])

    assert config.directories == [directory.resolve()]
    assert config.files == [diagram.resolve()]


def test_config_rejects_unsupported_file(tmp_path):
    """A file with an unsupported extension is rejected."""
    bad = tmp_path / "notes.txt"
    bad.write_text("hello")

    with pytest.raises(ValueError):
        Config.from_cli_args([bad])


def test_config_rejects_missing_path(tmp_path):
    """A path that does not exist is rejected."""
    missing = tmp_path / "nope.dot"

    with pytest.raises(ValueError):
        Config.from_cli_args([missing])


def test_config_allows_empty():
    """An empty watch set is allowed (the server can start watching nothing)."""
    config = Config(directories=[], files=[])
    assert config.directories == []
    assert config.files == []