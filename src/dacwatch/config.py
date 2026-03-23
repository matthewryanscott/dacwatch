from pathlib import Path
from urllib.parse import urlparse
from dataclasses import dataclass, field


@dataclass
class Config:
    """Configuration for DaCWatch application."""

    directories: list[Path] = field(default_factory=list)
    kroki_base: str = "http://localhost:48000"

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_directories()
        self._validate_kroki_base()

    def _validate_directories(self):
        """Validate that all directories exist and are directories."""
        if not self.directories:
            raise ValueError("At least one directory must be specified")
        for directory in self.directories:
            if not directory.exists():
                raise ValueError(f"Directory does not exist: {directory}")
            if not directory.is_dir():
                raise ValueError(f"Path is not a directory: {directory}")

    def _validate_kroki_base(self):
        """Validate that kroki_base is a valid URL."""
        try:
            parsed = urlparse(self.kroki_base)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"Invalid URL: {self.kroki_base}")
        except Exception as e:
            raise ValueError(f"Invalid kroki_base URL: {self.kroki_base}") from e

    @classmethod
    def from_cli_args(cls, directories: list[Path], kroki_base: str = "http://localhost:48000") -> "Config":
        """Create Config from CLI arguments."""
        return cls(directories=directories, kroki_base=kroki_base)