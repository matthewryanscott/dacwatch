from pathlib import Path
from urllib.parse import urlparse
from dataclasses import dataclass, field

from .file_type import is_supported_file


@dataclass
class Config:
    """Configuration for DaCWatch application."""

    directories: list[Path] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)
    kroki_base: str = "http://localhost:48000"

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_paths()
        self._validate_kroki_base()

    def _validate_paths(self):
        """Validate that all watched directories and files exist and are usable.

        An empty set is allowed: the singleton server can start watching nothing
        (e.g. launched from the .app bundle) and receive paths later over IPC.
        """
        for directory in self.directories:
            if not directory.exists():
                raise ValueError(f"Directory does not exist: {directory}")
            if not directory.is_dir():
                raise ValueError(f"Path is not a directory: {directory}")
        for file in self.files:
            if not file.exists():
                raise ValueError(f"File does not exist: {file}")
            if not file.is_file():
                raise ValueError(f"Path is not a file: {file}")
            if not is_supported_file(file):
                raise ValueError(f"Unsupported file type: {file}")

    def _validate_kroki_base(self):
        """Validate that kroki_base is a valid URL."""
        try:
            parsed = urlparse(self.kroki_base)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"Invalid URL: {self.kroki_base}")
        except Exception as e:
            raise ValueError(f"Invalid kroki_base URL: {self.kroki_base}") from e

    @classmethod
    def from_cli_args(cls, paths: list[Path], kroki_base: str = "http://localhost:48000") -> "Config":
        """Create Config from CLI arguments, classifying each path as a dir or file."""
        directories: list[Path] = []
        files: list[Path] = []
        for raw in paths:
            p = Path(raw).resolve()
            # A path that exists and is a directory is a watch-root; everything
            # else is treated as a file (validation will reject bad entries).
            if p.is_dir():
                directories.append(p)
            else:
                files.append(p)
        return cls(directories=directories, files=files, kroki_base=kroki_base)
