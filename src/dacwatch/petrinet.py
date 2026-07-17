"""Optional .petrinet support via the velocitron-viz CLI.

On startup dacwatch looks for velocitron-viz on PATH. When present, .petrinet
files are supported: velocitron-viz transforms the document into Graphviz DOT,
which is then rendered through Kroki like any other graphviz source.
"""

import asyncio
import functools
import shutil

VELOCITRON_VIZ = "velocitron-viz"


class PetrinetTransformError(Exception):
    """velocitron-viz failed to transform a .petrinet document."""

    def __init__(self, message: str, detail: str = ""):
        self.detail = detail
        super().__init__(message)


@functools.cache
def velocitron_viz_path() -> str | None:
    """Locate the velocitron-viz CLI on PATH (checked once, then cached)."""
    return shutil.which(VELOCITRON_VIZ)


def is_petrinet_supported() -> bool:
    """Whether .petrinet files can be rendered (velocitron-viz installed)."""
    return velocitron_viz_path() is not None


async def petrinet_to_dot(file_path: str) -> str:
    """Transform a .petrinet document into Graphviz DOT source.

    Args:
        file_path: Path to the .petrinet file

    Returns:
        DOT source emitted by velocitron-viz

    Raises:
        PetrinetTransformError: If velocitron-viz is missing or exits nonzero
    """
    viz = velocitron_viz_path()
    if viz is None:
        raise PetrinetTransformError("velocitron-viz is not installed")

    # --plain-labels: Kroki's graphviz rejects the HTML-like labels
    # velocitron-viz emits by default (marking token tables fail to parse).
    process = await asyncio.create_subprocess_exec(
        viz,
        "--plain-labels",
        str(file_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise PetrinetTransformError(
            f"velocitron-viz exited with status {process.returncode}",
            stderr.decode("utf-8", errors="replace"),
        )
    return stdout.decode("utf-8")
