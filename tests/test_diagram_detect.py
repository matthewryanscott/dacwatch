import pytest

from dacwatch.diagram_detect import (
    DETECTION_CANDIDATES,
    guess_diagram_type,
    ordered_candidates,
    detect_and_render,
)
from dacwatch.kroki_client import KrokiError


MERMAID_SOURCE = """flowchart TD
    A[Start] --> B{Decision}
    B -->|Yes| C[OK]
    B -->|No| D[Stop]
"""

PLANTUML_SOURCE = """@startuml
Alice -> Bob: Hello
@enduml
"""

GRAPHVIZ_SOURCE = """digraph G {
    a -> b;
    b -> c;
}
"""


class TestGuessDiagramType:
    @pytest.mark.parametrize("source,expected", [
        ("graph TD\n A-->B", "mermaid"),
        ("flowchart LR\n A-->B", "mermaid"),
        ("sequenceDiagram\n Alice->>Bob: hi", "mermaid"),
        ("classDiagram\n class Foo", "mermaid"),
        ("stateDiagram-v2\n [*] --> S1", "mermaid"),
        ("erDiagram\n CUSTOMER ||--o{ ORDER : places", "mermaid"),
        ("gantt\n title A", "mermaid"),
        ("pie title Pets\n \"Dogs\": 1", "mermaid"),
        ("mindmap\n root", "mermaid"),
    ])
    def test_detects_mermaid(self, source, expected):
        assert guess_diagram_type(source) == expected

    @pytest.mark.parametrize("source", [
        PLANTUML_SOURCE,
        "@startmindmap\n* root\n@endmindmap",
        "   \n@startuml\na->b\n@enduml",
    ])
    def test_detects_plantuml(self, source):
        assert guess_diagram_type(source) == "plantuml"

    @pytest.mark.parametrize("source", [
        GRAPHVIZ_SOURCE,
        "strict digraph {\n a->b\n}",
        "graph G {\n a -- b\n}",
    ])
    def test_detects_graphviz(self, source):
        assert guess_diagram_type(source) == "graphviz"

    def test_returns_none_for_empty(self):
        assert guess_diagram_type("") is None
        assert guess_diagram_type("   \n  ") is None

    def test_returns_none_for_unknown(self):
        assert guess_diagram_type("just some random prose text") is None


class TestOrderedCandidates:
    def test_includes_all_candidates(self):
        ordered = ordered_candidates(MERMAID_SOURCE)
        assert set(ordered) == set(DETECTION_CANDIDATES)

    def test_guess_comes_first(self):
        assert ordered_candidates(GRAPHVIZ_SOURCE)[0] == "graphviz"
        assert ordered_candidates(PLANTUML_SOURCE)[0] == "plantuml"
        assert ordered_candidates(MERMAID_SOURCE)[0] == "mermaid"

    def test_no_duplicates(self):
        ordered = ordered_candidates(MERMAID_SOURCE)
        assert len(ordered) == len(set(ordered))

    def test_unknown_keeps_default_order(self):
        ordered = ordered_candidates("random prose")
        assert ordered == list(DETECTION_CANDIDATES)


class _FakeKroki:
    """Fake Kroki client: succeeds only for the configured type."""

    def __init__(self, good_type, *, fail_status=400):
        self.good_type = good_type
        self.fail_status = fail_status
        self.calls = []

    async def render_diagram(self, source, diagram_type, format):
        self.calls.append((diagram_type, format))
        if diagram_type == self.good_type:
            return b"<svg>ok</svg>"
        raise KrokiError(self.fail_status, "Bad", "syntax error", url="x")


def _fmt(diagram_type):
    return "png" if diagram_type == "mermaid" else "svg"


class TestDetectAndRender:
    @pytest.mark.asyncio
    async def test_returns_first_matching_type(self):
        client = _FakeKroki("mermaid")
        result = await detect_and_render(client, MERMAID_SOURCE, _fmt)
        assert result is not None
        dtype, fmt, data = result
        assert dtype == "mermaid"
        assert fmt == "png"
        assert data == b"<svg>ok</svg>"

    @pytest.mark.asyncio
    async def test_skips_400_and_finds_later_candidate(self):
        client = _FakeKroki("graphviz")
        # Source heuristically looks like graphviz so it's tried first anyway,
        # but force a mermaid-looking source to exercise fallthrough.
        result = await detect_and_render(client, MERMAID_SOURCE, _fmt)
        assert result is not None
        assert result[0] == "graphviz"
        # mermaid (guessed) was tried before graphviz
        assert ("mermaid", "png") in client.calls

    @pytest.mark.asyncio
    async def test_returns_none_when_nothing_matches(self):
        client = _FakeKroki("nonexistent-type")
        result = await detect_and_render(client, MERMAID_SOURCE, _fmt)
        assert result is None
        # Every candidate was attempted
        assert len(client.calls) == len(DETECTION_CANDIDATES)

    @pytest.mark.asyncio
    async def test_propagates_server_error(self):
        client = _FakeKroki("nonexistent-type", fail_status=502)
        with pytest.raises(KrokiError):
            await detect_and_render(client, MERMAID_SOURCE, _fmt)
