import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DiagramBlock:
    index: int           # 0-based among diagram blocks only
    diagram_type: str    # "plantuml", "mermaid", "graphviz"
    source: str          # Code block content (without fence markers)


# Mapping of fence languages to Kroki diagram types (case-insensitive)
FENCE_LANG_TO_TYPE = {
    'plantuml': 'plantuml',
    'puml': 'plantuml',
    'mermaid': 'mermaid',
    'dot': 'graphviz',
    'graphviz': 'graphviz',
}

# Regex to match fenced code blocks: ```lang\n...\n```
_FENCE_PATTERN = re.compile(
    r'^```(\w+)\s*\n(.*?)^```\s*$',
    re.MULTILINE | re.DOTALL
)


def extract_diagram_blocks(content: str) -> list[DiagramBlock]:
    """Extract diagram code blocks from markdown content.

    Only returns blocks whose fence language maps to a supported diagram type.
    Non-diagram code fences (e.g. ```python) are skipped.

    Args:
        content: Markdown file content

    Returns:
        List of DiagramBlock, indexed 0-based among diagram blocks only
    """
    blocks = []
    for match in _FENCE_PATTERN.finditer(content):
        lang = match.group(1).lower()
        diagram_type = FENCE_LANG_TO_TYPE.get(lang)
        if diagram_type:
            blocks.append(DiagramBlock(
                index=len(blocks),
                diagram_type=diagram_type,
                source=match.group(2),
            ))
    return blocks


def is_markdown_file(file_path: Path) -> bool:
    """Check if a file is a markdown file.

    Args:
        file_path: Path to the file

    Returns:
        True if the file has a .md extension
    """
    return file_path.suffix.lower() == '.md'
