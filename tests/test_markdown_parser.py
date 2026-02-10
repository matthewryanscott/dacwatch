import pytest
from pathlib import Path

from dacwatch.markdown_parser import extract_diagram_blocks, is_markdown_file, DiagramBlock


class TestIsMarkdownFile:
    """Test suite for is_markdown_file."""

    def test_md_extension(self):
        assert is_markdown_file(Path("readme.md")) is True

    def test_md_extension_uppercase(self):
        assert is_markdown_file(Path("README.MD")) is True

    def test_md_extension_mixed_case(self):
        assert is_markdown_file(Path("Notes.Md")) is True

    def test_non_md_extensions(self):
        assert is_markdown_file(Path("file.txt")) is False
        assert is_markdown_file(Path("file.dot")) is False
        assert is_markdown_file(Path("file.puml")) is False
        assert is_markdown_file(Path("file.py")) is False

    def test_no_extension(self):
        assert is_markdown_file(Path("README")) is False

    def test_nested_path(self):
        assert is_markdown_file(Path("/some/deep/path/docs.md")) is True


class TestExtractDiagramBlocks:
    """Test suite for extract_diagram_blocks."""

    def test_empty_content(self):
        assert extract_diagram_blocks("") == []

    def test_no_fences(self):
        content = "# Hello\n\nSome text without code fences.\n"
        assert extract_diagram_blocks(content) == []

    def test_non_diagram_fences_ignored(self):
        content = "```python\nprint('hello')\n```\n\n```javascript\nconsole.log('hi');\n```\n"
        assert extract_diagram_blocks(content) == []

    def test_single_plantuml_block(self):
        content = "# Diagram\n\n```plantuml\n@startuml\nA -> B\n@enduml\n```\n"
        blocks = extract_diagram_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].index == 0
        assert blocks[0].diagram_type == "plantuml"
        assert "@startuml\nA -> B\n@enduml\n" == blocks[0].source

    def test_single_mermaid_block(self):
        content = "```mermaid\ngraph TD\n  A --> B\n```\n"
        blocks = extract_diagram_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].index == 0
        assert blocks[0].diagram_type == "mermaid"
        assert "graph TD\n  A --> B\n" == blocks[0].source

    def test_single_dot_block(self):
        content = "```dot\ndigraph G { A -> B; }\n```\n"
        blocks = extract_diagram_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].index == 0
        assert blocks[0].diagram_type == "graphviz"

    def test_single_graphviz_block(self):
        content = "```graphviz\ndigraph G { A -> B; }\n```\n"
        blocks = extract_diagram_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].diagram_type == "graphviz"

    def test_puml_alias(self):
        content = "```puml\n@startuml\nA -> B\n@enduml\n```\n"
        blocks = extract_diagram_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].diagram_type == "plantuml"

    def test_multiple_blocks(self):
        content = (
            "# Doc\n\n"
            "```plantuml\n@startuml\nA -> B\n@enduml\n```\n\n"
            "Some text\n\n"
            "```mermaid\ngraph TD\n  A --> B\n```\n\n"
            "More text\n\n"
            "```dot\ndigraph G { X -> Y; }\n```\n"
        )
        blocks = extract_diagram_blocks(content)
        assert len(blocks) == 3
        assert blocks[0].index == 0
        assert blocks[0].diagram_type == "plantuml"
        assert blocks[1].index == 1
        assert blocks[1].diagram_type == "mermaid"
        assert blocks[2].index == 2
        assert blocks[2].diagram_type == "graphviz"

    def test_mixed_diagram_and_non_diagram(self):
        """Non-diagram fences don't affect indexing of diagram blocks."""
        content = (
            "```python\nprint('hello')\n```\n\n"
            "```plantuml\n@startuml\nA -> B\n@enduml\n```\n\n"
            "```javascript\nconsole.log('hi');\n```\n\n"
            "```mermaid\ngraph TD\n  A --> B\n```\n"
        )
        blocks = extract_diagram_blocks(content)
        assert len(blocks) == 2
        assert blocks[0].index == 0
        assert blocks[0].diagram_type == "plantuml"
        assert blocks[1].index == 1
        assert blocks[1].diagram_type == "mermaid"

    def test_case_insensitive_fence_lang(self):
        content = "```PlantUML\n@startuml\nA -> B\n@enduml\n```\n"
        blocks = extract_diagram_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].diagram_type == "plantuml"

    def test_case_insensitive_mermaid(self):
        content = "```MERMAID\ngraph TD\n  A --> B\n```\n"
        blocks = extract_diagram_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].diagram_type == "mermaid"

    def test_case_insensitive_dot(self):
        content = "```DOT\ndigraph G { A -> B; }\n```\n"
        blocks = extract_diagram_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].diagram_type == "graphviz"

    def test_all_supported_languages(self):
        """All supported fence languages map correctly."""
        languages = {
            'plantuml': 'plantuml',
            'puml': 'plantuml',
            'mermaid': 'mermaid',
            'dot': 'graphviz',
            'graphviz': 'graphviz',
        }
        for lang, expected_type in languages.items():
            content = f"```{lang}\ncontent\n```\n"
            blocks = extract_diagram_blocks(content)
            assert len(blocks) == 1, f"Expected 1 block for {lang}"
            assert blocks[0].diagram_type == expected_type, f"Expected {expected_type} for {lang}"

    def test_diagram_block_dataclass(self):
        block = DiagramBlock(index=0, diagram_type="plantuml", source="A -> B")
        assert block.index == 0
        assert block.diagram_type == "plantuml"
        assert block.source == "A -> B"
