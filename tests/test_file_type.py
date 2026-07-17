import pytest
from pathlib import Path
import sys

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dacwatch.file_type import get_diagram_type, is_supported_file


def test_get_diagram_type_dot():
    """Test .dot files map to graphviz."""
    path = Path("diagram.dot")
    assert get_diagram_type(path) == "graphviz"


def test_get_diagram_type_puml():
    """Test .puml files map to plantuml."""
    path = Path("diagram.puml")
    assert get_diagram_type(path) == "plantuml"


def test_get_diagram_type_plantuml():
    """Test .plantuml files map to plantuml."""
    path = Path("diagram.plantuml")
    assert get_diagram_type(path) == "plantuml"


def test_get_diagram_type_mermaid():
    """Test .mermaid files map to mermaid."""
    path = Path("diagram.mermaid")
    assert get_diagram_type(path) == "mermaid"


def test_get_diagram_type_unsupported():
    """Test unsupported files return None."""
    path = Path("diagram.txt")
    assert get_diagram_type(path) is None

    path = Path("diagram.py")
    assert get_diagram_type(path) is None


def test_get_diagram_type_case_insensitive():
    """Test file extension matching is case insensitive."""
    path = Path("diagram.DOT")
    assert get_diagram_type(path) == "graphviz"

    path = Path("diagram.PUML")
    assert get_diagram_type(path) == "plantuml"

    path = Path("diagram.MERMAID")
    assert get_diagram_type(path) == "mermaid"


def test_is_supported_file():
    """Test is_supported_file function."""
    assert is_supported_file(Path("diagram.dot")) is True
    assert is_supported_file(Path("diagram.puml")) is True
    assert is_supported_file(Path("diagram.plantuml")) is True
    assert is_supported_file(Path("diagram.mermaid")) is True
    assert is_supported_file(Path("docs.md")) is True

    assert is_supported_file(Path("diagram.txt")) is False
    assert is_supported_file(Path("diagram.py")) is False


def test_is_supported_file_markdown():
    """Test that markdown files are supported."""
    assert is_supported_file(Path("README.md")) is True
    assert is_supported_file(Path("notes.MD")) is True
    assert is_supported_file(Path("/path/to/docs.md")) is True


def test_markdown_not_a_diagram_type():
    """Test that .md files don't have a diagram type (they're parsed differently)."""
    assert get_diagram_type(Path("docs.md")) is None


def test_get_diagram_type_no_extension():
    """Test files without extension."""
    path = Path("diagram")
    assert get_diagram_type(path) is None


def test_get_diagram_type_petrinet_supported(monkeypatch):
    """Test .petrinet files map to petrinet when velocitron-viz is installed."""
    monkeypatch.setattr("dacwatch.file_type.is_petrinet_supported", lambda: True)
    assert get_diagram_type(Path("net.petrinet")) == "petrinet"
    assert get_diagram_type(Path("net.PETRINET")) == "petrinet"
    assert is_supported_file(Path("net.petrinet")) is True


def test_get_diagram_type_petrinet_unsupported(monkeypatch):
    """Test .petrinet files are unsupported when velocitron-viz is missing."""
    monkeypatch.setattr("dacwatch.file_type.is_petrinet_supported", lambda: False)
    assert get_diagram_type(Path("net.petrinet")) is None
    assert is_supported_file(Path("net.petrinet")) is False