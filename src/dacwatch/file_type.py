from pathlib import Path
from typing import Optional

from .markdown_parser import is_markdown_file
from .petrinet import is_petrinet_supported


# Mapping of file extensions to diagram types
EXTENSION_TO_TYPE = {
    '.dot': 'graphviz',
    '.puml': 'plantuml',
    '.plantuml': 'plantuml',
    '.mermaid': 'mermaid',
}

# Supported only when the velocitron-viz CLI is installed (transforms to DOT)
PETRINET_EXTENSION = '.petrinet'


def get_diagram_type(file_path: Path) -> Optional[str]:
    """
    Get the diagram type for a file based on its extension.

    Args:
        file_path: Path to the file

    Returns:
        Diagram type string or None if not supported
    """
    extension = file_path.suffix.lower()
    if extension == PETRINET_EXTENSION:
        return 'petrinet' if is_petrinet_supported() else None
    return EXTENSION_TO_TYPE.get(extension)


def is_supported_file(file_path: Path) -> bool:
    """
    Check if a file is a supported diagram or markdown file.

    Args:
        file_path: Path to the file

    Returns:
        True if the file is supported, False otherwise
    """
    return get_diagram_type(file_path) is not None or is_markdown_file(file_path)