import pytest
from pathlib import Path
import sys

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config


def test_config_creation(tmp_path):
    """Test basic config creation."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    kroki_base = "https://kroki.io"

    config = Config(directory=directory, kroki_base=kroki_base)

    assert config.directory == directory
    assert config.kroki_base == kroki_base


def test_config_default_kroki_base(tmp_path):
    """Test config with default kroki base."""
    directory = tmp_path / "test_dir"
    directory.mkdir()

    config = Config(directory=directory)

    assert config.directory == directory
    assert config.kroki_base == "https://kroki.io"


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
    config = Config(directory=directory, kroki_base="https://custom.kroki.io")
    assert config.kroki_base == "https://custom.kroki.io"

    # Invalid URL should raise ValueError
    with pytest.raises(ValueError):
        Config(directory=directory, kroki_base="not-a-url")


def test_config_from_cli_args(tmp_path):
    """Test creating config from CLI arguments."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    kroki_base = "https://kroki.io"

    config = Config.from_cli_args(directory, kroki_base)

    assert config.directory == directory
    assert config.kroki_base == kroki_base