from pathlib import Path
from urllib.parse import urlparse
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration for DaCWatch application."""

    directory: Path
    kroki_base: str = "http://localhost:48000"

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_directory()
        self._validate_kroki_base()

    def _validate_directory(self):
        """Validate that directory exists and is a directory."""
        if not self.directory.exists():
            raise ValueError(f"Directory does not exist: {self.directory}")
        if not self.directory.is_dir():
            raise ValueError(f"Path is not a directory: {self.directory}")

    def _validate_kroki_base(self):
        """Validate that kroki_base is a valid URL."""
        try:
            parsed = urlparse(self.kroki_base)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"Invalid URL: {self.kroki_base}")
        except Exception as e:
            raise ValueError(f"Invalid kroki_base URL: {self.kroki_base}") from e

    @classmethod
    def from_cli_args(cls, directory: Path, kroki_base: str = "http://localhost:48000") -> "Config":
        """Create Config from CLI arguments."""
        return cls(directory=directory, kroki_base=kroki_base)