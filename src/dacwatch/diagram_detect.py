"""Diagram-type detection for source that carries no file extension.

Used when rendering diagram source pasted from the clipboard: there is no
filename to map to a Kroki type, so we guess the type from the source and, if
needed, brute-force the remaining candidates against the Kroki API.
"""

import re
from typing import Callable, Optional

from .kroki_client import KrokiClient, KrokiError

# Candidate types tried during detection, in default priority order. Mermaid
# leads because it is the most common clipboard paste; the others follow. This
# mirrors the file/fence types the rest of the app already supports.
DETECTION_CANDIDATES: tuple[str, ...] = ("mermaid", "plantuml", "graphviz")

# First-line keywords that identify a Mermaid diagram. Compared case-insensitively
# against the first non-empty source line.
_MERMAID_KEYWORDS = (
    "graph",
    "flowchart",
    "sequencediagram",
    "classdiagram",
    "statediagram",
    "statediagram-v2",
    "erdiagram",
    "journey",
    "gantt",
    "pie",
    "gitgraph",
    "mindmap",
    "timeline",
    "quadrantchart",
    "requirementdiagram",
    "sankey-beta",
    "xychart-beta",
    "block-beta",
    "c4context",
)

# Graphviz (DOT) opens with an optional `strict` then `graph`/`digraph`.
_GRAPHVIZ_RE = re.compile(r"^(strict\s+)?(di)?graph\b", re.IGNORECASE)


def _first_nonempty_line(source: str) -> str:
    for line in source.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def guess_diagram_type(source: str) -> Optional[str]:
    """Best-effort guess of the diagram type from the source text.

    Returns a Kroki diagram type, or None when nothing matches. The guess only
    orders the brute-force search (see ``ordered_candidates``); a wrong guess is
    self-correcting, so the heuristics stay deliberately simple.
    """
    text = source.strip()
    if not text:
        return None

    lowered = text.lower()

    # PlantUML wraps content in @start.../@end... directives.
    if "@start" in lowered:
        return "plantuml"

    first_line = _first_nonempty_line(text)

    # Graphviz starts with graph/digraph AND brace-delimits its body. Mermaid's
    # `graph TD` has no top-level brace, so the brace check disambiguates the
    # shared `graph` keyword.
    if _GRAPHVIZ_RE.match(first_line) and "{" in text:
        return "graphviz"

    first_word = first_line.split(maxsplit=1)[0].lower() if first_line else ""
    if first_word in _MERMAID_KEYWORDS or first_line.lower() in _MERMAID_KEYWORDS:
        return "mermaid"

    return None


def ordered_candidates(source: str) -> list[str]:
    """Return the candidate types to try, best guess first.

    Always returns every entry in ``DETECTION_CANDIDATES`` exactly once; an
    unrecognized source keeps the default order.
    """
    guess = guess_diagram_type(source)
    if guess is None or guess not in DETECTION_CANDIDATES:
        return list(DETECTION_CANDIDATES)
    return [guess] + [c for c in DETECTION_CANDIDATES if c != guess]


async def detect_and_render(
    kroki_client: KrokiClient,
    source: str,
    default_format: Callable[[str], str],
) -> Optional[tuple[str, str, bytes]]:
    """Detect a diagram's type by rendering it against candidate types.

    Tries each candidate (best guess first) in its default format. The first
    type that renders successfully wins and its image is returned, so the caller
    needs no second request. A 400 (syntax error for that type) just moves on to
    the next candidate; other errors (network, 5xx) propagate to the caller.

    Returns ``(diagram_type, format, image_data)`` on success, or None when no
    candidate type accepts the source.
    """
    for diagram_type in ordered_candidates(source):
        fmt = default_format(diagram_type)
        try:
            image_data = await kroki_client.render_diagram(source, diagram_type, fmt)
            return diagram_type, fmt, image_data
        except KrokiError as exc:
            if exc.status == 400:
                continue  # Wrong type for this source; try the next candidate.
            raise
    return None
